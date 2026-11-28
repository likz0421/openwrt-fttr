//! Linux network setup from a selected platform's topology.
use crate::platform::resources::Resources;
use std::{io, process::Command};

pub fn setup_bridge(resources: &Resources, bridge: &str) -> io::Result<()> {
    for interface in resources.management_interfaces {
        if interface_present(interface) {
            let _ = link(&["set", interface, "up"]);
        }
    }
    for interface in resources.downstream_interfaces {
        if !interface_present(interface) {
            continue;
        }
        link(&["set", interface, "up"])?;
        link(&["set", interface, "master", bridge])?;
    }
    Ok(())
}

/// Bridge only the first `ports` downstream interfaces into `bridge`.
/// Any remaining downstream interface is detached from the bridge and shut
/// down, so br-lan exposes exactly the configured number of fttr ports.
/// A `ports` value of 0 (or larger than the platform count) means "all".
/// True when the kernel actually created this netdev. With the reduced kmod
/// (FMCS_ACTIVE_FTTR_PORTS=2) only fttr1/fttr2 exist; the platform resource
/// table still lists all 16, so guard every access to avoid "Cannot find
/// device" errors and spurious failures.
fn interface_present(interface: &str) -> bool {
    std::path::Path::new("/sys/class/net").join(interface).exists()
}

pub fn setup_bridge_limited(
    resources: &Resources,
    bridge: &str,
    ports: usize,
) -> io::Result<()> {
    for interface in resources.management_interfaces {
        // Management interfaces may be absent on a reduced build; skip them
        // instead of failing the whole startup.
        if interface_present(interface) {
            let _ = link(&["set", interface, "up"]);
        }
    }
    let total = resources.downstream_interfaces.len();
    let active = if ports == 0 { total } else { ports.min(total) };
    for (index, interface) in resources.downstream_interfaces.iter().enumerate() {
        // Never touch a netdev the kmod did not create.
        if !interface_present(interface) {
            continue;
        }
        if index < active {
        link(&["set", interface, "up"])?;
        link(&["set", interface, "master", bridge])?;
        } else {
            let _ = link(&["set", interface, "nomaster"]);
            let _ = link(&["set", interface, "down"]);
        }
    }
    Ok(())
}

fn link(args: &[&str]) -> io::Result<()> {
    let status = Command::new("ip").arg("link").args(args).status()?;
    if status.success() {
        Ok(())
    } else {
        Err(io::Error::other(format!(
            "ip link {}: {status}",
            args.join(" ")
        )))
    }
}
