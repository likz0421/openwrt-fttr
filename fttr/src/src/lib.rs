#[cfg(feature = "acs")]
pub mod acs;
pub mod acs_cli;
pub mod adapters;
pub(crate) mod bootstrap;
#[cfg(feature = "mqtt")]
pub mod broker;
pub mod capabilities;
pub mod controller;
pub mod cwmp;
pub mod devices;
pub mod domain;
pub mod hl202_ipc;
pub mod ipc;
pub mod model;
#[cfg(feature = "mqtt")]
pub mod mqtt;
pub mod mqtt_identity;
/// Optional offload API; implementations live with their hardware platform.
pub mod npu {
    #[cfg(not(all(feature = "npu", feature = "platform-h3c-hm2004-du")))]
    use crate::model::NpuStatus;
    #[cfg(all(feature = "npu", feature = "platform-h3c-hm2004-du"))]
    pub use crate::platform::h3c_hm2004_du::offload::*;
    #[cfg(not(all(feature = "npu", feature = "platform-h3c-hm2004-du")))]
    pub fn status() -> NpuStatus {
        NpuStatus::default()
    }
}
#[cfg(any(feature = "mqtt", test))]
mod mqtt_limits;
pub mod omci_auth;
pub mod optical;
pub mod platform;
pub mod pon_engine;
pub(crate) mod ports;
pub mod provisioning;
pub mod provisioning_cli;
mod runtime;
#[cfg(any(feature = "mqtt", test))]
mod telemetry_sources;

// Unit fixtures which prove the MQTT-off boundary share the production port.
#[cfg(all(test, not(feature = "mqtt")))]
pub(crate) static MQTT_TEST_PORT: std::sync::Mutex<()> = std::sync::Mutex::new(());
