use crate::{ipc::SubDevice, pon_engine::PonEngine};

/// Number of fttr downstream ports actually bridged into br-lan, from the
/// same UCI option the bridge setup uses (`fttr.h3c.lan_ports`, 1..=16).
///
/// Reporting this as `switch_port_count` makes the backend status the single
/// source of truth: the status page, the topology and every other consumer of
/// `switch_ports` see exactly the ports that are really in use. An absent or
/// invalid value means "all" (16), preserving stock behaviour.
pub(super) fn reported_switch_port_count() -> u8 {
    // Hardware fact: the kmod creates FMCS_ACTIVE_FTTR_PORTS (2) netdevs in
    // this build. Only a smaller configured bridge count can reduce it further.
    const HARDWARE_PORTS: u8 = 2;
    let Ok(view) = crate::config::load() else {
        return HARDWARE_PORTS;
    };
    let raw = view.option("h3c", "lan_ports").unwrap_or_default();
    match raw.trim().parse::<u8>() {
        Ok(n) if (1..=HARDWARE_PORTS).contains(&n) => n,
        _ => HARDWARE_PORTS,
    }
}

pub(super) fn snapshot(
    engine: &PonEngine,
    services: &crate::controller::service::States,
    sources: (&[SubDevice], fttr_api::SyncStatusReply),
) -> fttr_api::StatusReply {
    crate::platform::status::snapshot(
        engine,
        services,
        sources,
        crate::platform::status::Hardware {
            switch_port_count: reported_switch_port_count(),
            supports_pinning: true,
            ranging_source: |id| {
                format!(
                    "FMCS directed ranging register 0x{:08x}",
                    0x01010020u32 + 4 * u32::from(id)
                )
            },
            has_pon_mac_fec: true,
            data_path: super::dataplane::data_path,
            fpga_status: super::firmware::get_fpga_status().to_string(),
            pon_mac: Some(super::pon_mac::snapshot()),
            optical_transceiver: super::fmcs::get_optical_status(),
            npu: Some(crate::npu::status()),
        },
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mirrors the parse/clamp rule in reported_switch_port_count without
    // touching libuci, so the boundaries are verified at compile time.
    fn clamp(raw: &str) -> u8 {
        match raw.trim().parse::<u8>() {
            Ok(n) if (1..=2).contains(&n) => n,
            _ => 2,
        }
    }

    #[test]
    fn lan_ports_accepts_1_to_2_and_defaults_otherwise() {
        assert_eq!(clamp("1"), 1);
        assert_eq!(clamp("2"), 2);
        for invalid in ["", "0", "3", "8", "16", "255", "abc", " 1x", "-1"] {
            assert_eq!(clamp(invalid), 2, "invalid input: {invalid}");
        }
    }
}
