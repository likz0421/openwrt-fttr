//! Desired downstream capacity. Kernel registration changes only at boot.
use std::{fs, path::Path, process::Command};

pub(crate) const MAX_PORTS: u8 = 16;
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Ports {
    pub enabled: bool,
    pub count: u8,
}
impl Default for Ports {
    fn default() -> Self {
        // Upgrades with no section retain the historical sixteen ports.
        Self {
            enabled: true,
            count: MAX_PORTS,
        }
    }
}
impl Ports {
    pub fn active(self) -> u8 {
        if self.enabled {
            self.count
        } else {
            0
        }
    }
}

pub(crate) fn parse(text: &str) -> Result<Ports, String> {
    let sections = crate::provisioning::config::parse_sections(text)?;
    let mut found = sections.iter().filter(|(_, s)| s.kind == "ports");
    let Some((name, s)) = found.next() else {
        return Ok(Ports::default());
    };
    if name != "ports" || found.next().is_some() {
        return Err("use one named config ports 'ports' section".into());
    }
    for (key, values) in &s.options {
        if !["enabled", "count"].contains(&key.as_str()) || values.len() != 1 {
            return Err("ports requires scalar enabled and count options".into());
        }
    }
    let enabled = match s.get("enabled") {
        "" | "1" | "true" | "yes" | "on" => true,
        "0" | "false" | "no" | "off" => false,
        _ => return Err("invalid ports enabled boolean".into()),
    };
    let count = match s.get("count") {
        "" => MAX_PORTS,
        value if value.bytes().all(|b| b.is_ascii_digit()) => value
            .parse::<u8>()
            .ok()
            .filter(|n| (1..=MAX_PORTS).contains(n))
            .ok_or("ports count must be 1..16")?,
        _ => return Err("ports count must be 1..16".into()),
    };
    Ok(Ports { enabled, count })
}

/// Runtime capacity comes from the immutable driver, never from a pending UCI edit.
/// Old drivers have no parameter; inspect actual registered interfaces instead.
pub(crate) fn runtime_count(parameter: &Path, net: &Path) -> u8 {
    if let Ok(value) = fs::read_to_string(parameter) {
        return value
            .trim()
            .parse::<u8>()
            .ok()
            .filter(|n| *n <= MAX_PORTS)
            .unwrap_or(0);
    }
    (1..=MAX_PORTS)
        .take_while(|n| net.join(format!("fttr{n}")).exists())
        .count() as u8
}

/// Used by the existing configReload contract; only prepares the next boot.
pub(crate) fn prepare_boot() -> Result<(), String> {
    let script = Path::new("/usr/libexec/fttr-ports");
    if !script.exists() {
        return Ok(());
    } // Host tests and non-OpenWrt builds.
    let status = Command::new(script)
        .arg("prepare")
        .status()
        .map_err(|e| e.to_string())?;
    if status.success() {
        Ok(())
    } else {
        Err("cannot prepare FTTR boot ports".into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn legacy_disabled_and_capacity_boundaries() {
        assert_eq!(parse("").unwrap().active(), 16);
        for count in [1, 4, 16] {
            let text =
                format!("config ports 'ports'\n option enabled '1'\n option count '{count}'\n");
            assert_eq!(parse(&text).unwrap().active(), count);
            assert_eq!(
                parse(&text.replace("enabled '1'", "enabled '0'"))
                    .unwrap()
                    .active(),
                0
            );
        }
        for value in ["0", "17", "-1", "+4", "4.0", "abc", "256"] {
            assert!(parse(&format!("config ports 'ports'\n option count '{value}'\n")).is_err());
        }
        for text in [
            "config ports wrong",
            "config ports ports\noption enabled maybe",
            "config ports ports\nlist count 4\nlist count 5",
        ] {
            assert!(parse(text).is_err(), "{text}");
        }
    }
}
