include $(TOPDIR)/rules.mk

PKG_NAME:=openwrt-fttr
PKG_VERSION:=0.1.0
PKG_RELEASE:=2
PKG_LICENSE:=Apache-2.0
PKG_URL:=https://github.com/LazuliKao/openwrt-fttr/tree/main/fttr

PKG_BUILD_DEPENDS:=rust/host
PKG_BUILD_PARALLEL:=1
PKG_CONFIG_DEPENDS:=CONFIG_FTTR_PLATFORM_H3C_HM2004_DU CONFIG_FTTR_PLATFORM_FIBERHOME_AN4475_G2 CONFIG_FTTR_PLATFORM_TIANYI_TYFZA1 CONFIG_FTTR_DEVICE_HL202 CONFIG_FTTR_DEVICE_HWTC CONFIG_FTTR_DEVICE_STAR CONFIG_FTTR_DEVICE_ZTE CONFIG_FTTR_DEVICE_SCTY CONFIG_FTTR_DEVICE_FIBERHOME CONFIG_FTTR_DEVICE_REALTEK CONFIG_FTTR_ACS CONFIG_FTTR_MQTT CONFIG_FTTR_NPU CONFIG_FTTR_MIMALLOC

include $(INCLUDE_DIR)/package.mk
include $(TOPDIR)/feeds/packages/lang/rust/rust-package.mk

define Package/openwrt-fttr
  SECTION:=net
  CATEGORY:=Network
  SUBMENU:=PON
  TITLE:=OpenWrt FTTR controller and device management tools
  DEPENDS:=$(RUST_ARCH_DEPENDS) +FTTR_PLATFORM_H3C_HM2004_DU:kmod-h3c-fmcs +FTTR_NPU&&FTTR_PLATFORM_H3C_HM2004_DU:airoha-en7581-npu-firmware +uci +ubus +firewall4 +dnsmasq
endef

define Package/openwrt-fttr/description
 Pure-Rust FTTR userspace controller, optical platform management, and device adapters.
 Supports multiple downstream FTTR device vendors through compile-time selectable adapters.
endef

define Package/openwrt-fttr/config
  config FTTR_PLATFORM_H3C_HM2004_DU
    bool "Compile H3C HM2004-DU platform backend"
    depends on PACKAGE_openwrt-fttr
    default y
  config FTTR_PLATFORM_FIBERHOME_AN4475_G2
    bool "Compile FiberHome AN4475-G2 platform stub (hardware support pending)"
    depends on PACKAGE_openwrt-fttr
    default n
  config FTTR_PLATFORM_TIANYI_TYFZA1
    bool "Compile Tianyi TYFZA1 platform stub (hardware support pending)"
    depends on PACKAGE_openwrt-fttr
    default n
  config FTTR_DEVICE_HL202
    bool "Compile HL202-DU-C adapter (verified business and MQTT commands)"
    depends on PACKAGE_openwrt-fttr
    default y
  config FTTR_DEVICE_HWTC
    bool "Compile HWTC adapters (standard OMCI and model profiles)"
    depends on PACKAGE_openwrt-fttr
    default y
  config FTTR_DEVICE_STAR
    bool "Compile STAR adapter (SG631Z-C identity, generic OMCI bridge)"
    depends on PACKAGE_openwrt-fttr
    default y
  config FTTR_DEVICE_ZTE
    bool "Compile ZTE adapter (ZXHN G1612 identity, generic OMCI bridge)"
    depends on PACKAGE_openwrt-fttr
    default y
  config FTTR_DEVICE_SCTY
    bool "Compile SCTY TY-FS803G adapter (OMCI bridge only; CWMP unverified)"
    depends on PACKAGE_openwrt-fttr
    default y
  config FTTR_ACS
    bool "Compile embedded minimal CWMP ACS (runtime UCI switch)"
    depends on PACKAGE_openwrt-fttr
    default y
  config FTTR_DEVICE_FIBERHOME
    bool "Compile experimental FiberHome HG6371F-C / HG6371F bridge (explicit opt-in)"
    depends on PACKAGE_openwrt-fttr
    default y
  config FTTR_DEVICE_REALTEK
    bool "Compile experimental Realtek TYFCA1 OMCI bridge adapter"
    depends on PACKAGE_openwrt-fttr
    default y
  config FTTR_MQTT
    bool "Compile controller-owned MQTT broker and clients"
    depends on PACKAGE_openwrt-fttr
    default y
  config FTTR_MIMALLOC
    bool "Use mimalloc for fttrd Rust allocations (experimental)"
    depends on PACKAGE_openwrt-fttr
    default y
    help
      Select mimalloc 3.5.3 for the daemon only, without explicit THP advice.
      Compare target RSS, swap and service behavior before enabling in production.
  config FTTR_NPU
    bool "Compile fttrd NPU bridge offload coordination (runtime UCI switch)"
    depends on PACKAGE_openwrt-fttr && FTTR_PLATFORM_H3C_HM2004_DU
    default y
    help
      Coordinate driver admission and existing fw4 hooks inside fttrd.
      Disable to build without the NPU control service; software bridging remains available.
endef

RUST_PKG_FEATURES:=$(if $(CONFIG_FTTR_PLATFORM_H3C_HM2004_DU),platform-h3c-hm2004-du) $(if $(CONFIG_FTTR_PLATFORM_FIBERHOME_AN4475_G2),platform-fiberhome-an4475-g2) $(if $(CONFIG_FTTR_PLATFORM_TIANYI_TYFZA1),platform-tianyi-tyfza1) $(if $(CONFIG_FTTR_DEVICE_HL202),device-hl202) $(if $(CONFIG_FTTR_DEVICE_HWTC),device-hwtc) $(if $(CONFIG_FTTR_DEVICE_STAR),device-star) $(if $(CONFIG_FTTR_DEVICE_ZTE),device-zte) $(if $(CONFIG_FTTR_DEVICE_SCTY),device-scty) $(if $(CONFIG_FTTR_DEVICE_FIBERHOME),device-fiberhome) $(if $(CONFIG_FTTR_DEVICE_REALTEK),device-realtek) $(if $(CONFIG_FTTR_ACS),acs) $(if $(CONFIG_FTTR_MQTT),mqtt) $(if $(and $(CONFIG_FTTR_NPU),$(CONFIG_FTTR_PLATFORM_H3C_HM2004_DU)),npu) $(if $(CONFIG_FTTR_MIMALLOC),allocator-mimalloc)
# Keep production installation independent of workspace SDK/diagnostic binaries.
CARGO_PKG_ARGS+= --no-default-features --frozen --bin fttrd --bin fttrctl

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./src/Cargo.toml ./src/Cargo.lock $(PKG_BUILD_DIR)/
	$(CP) ./src/src $(PKG_BUILD_DIR)/
	[ -d ./src/crates ] && $(CP) ./src/crates $(PKG_BUILD_DIR)/ || true
	[ -d ./src/tools ] && $(CP) ./src/tools $(PKG_BUILD_DIR)/ || true
endef

# Populate the shared $(DL_DIR)/cargo registry and Git caches before compilation.
# Fetch every platform in Cargo.lock: cargo install --frozen can require sources
# excluded by fetch --target (e.g. encoding_rs -> core_detect on aarch64).
# --frozen above keeps the compile phase offline and enforces Cargo.lock.
define Build/Configure
	$(CARGO_PKG_VARS) cargo fetch --locked \
		--manifest-path $(PKG_BUILD_DIR)/Cargo.toml
endef

define Package/openwrt-fttr/install
	$(INSTALL_DIR) $(1)/usr/sbin
	$(INSTALL_BIN) $(PKG_INSTALL_DIR)/bin/fttrctl $(1)/usr/sbin/
	$(INSTALL_BIN) $(PKG_INSTALL_DIR)/bin/fttrd $(1)/usr/sbin/
	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./files/fttr.init $(1)/etc/init.d/fttr
	$(INSTALL_DIR) $(1)/etc/config
	$(INSTALL_CONF) ./files/fttr.config $(1)/etc/config/fttr
	$(INSTALL_DIR) $(1)/lib/upgrade/keep.d
	$(INSTALL_DATA) ./files/fttr.keep $(1)/lib/upgrade/keep.d/fttr
endef

define Package/openwrt-fttr/conffiles
/etc/config/fttr
endef

$(eval $(call RustBinPackage,openwrt-fttr))
$(eval $(call BuildPackage,openwrt-fttr))
