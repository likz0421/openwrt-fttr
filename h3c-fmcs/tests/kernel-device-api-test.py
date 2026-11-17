#!/usr/bin/env python3
"""Check actual SPI child matcher against both documented device API signatures."""
from pathlib import Path
import re, subprocess, tempfile
source=(Path(__file__).resolve().parents[1]/'src/fmcs_main.c').read_text()
start=source.index('/* device_find_child() made the match data const')
end=source.index('\nstatic struct spi_controller *fmcs_get_spi_controller',start)
matcher=source[start:end]
for version,const in [(612116,''),(613000,''),(614000,'const '),(618000,'const ')]:
 text='''#include <assert.h>
#include <string.h>
#include <stddef.h>
#define KERNEL_VERSION(a,b,c) ((a)*100000+(b)*1000+(c))
#define LINUX_VERSION_CODE VERSION
struct class { const char *name; };
struct device { const struct class *class; };
'''.replace('VERSION\n',str(version)+'\n')+matcher+'''
static struct device *device_find_child(struct device *dev, QUALvoid *data,
        int (*match)(struct device *, QUALvoid *)) {
 return match(dev,data) ? dev : NULL;
}
int main(void) {
 struct class spi={"spi_master"},other={"not-spi"};
 struct device a={&spi},b={&other},empty={NULL};
 assert(device_find_child(&a,NULL,fmcs_match_spi_child)==&a);
 assert(device_find_child(&b,NULL,fmcs_match_spi_child)==NULL);
 assert(device_find_child(&empty,NULL,fmcs_match_spi_child)==NULL);
 return 0;
}
'''.replace('QUAL',const)
 with tempfile.TemporaryDirectory() as d:
  p=Path(d);(p/'test.c').write_text(text)
  subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(p/'test.c'),'-o',str(p/'test')],check=True)
  subprocess.run([str(p/'test')],check=True)
 print('PASS actual matcher/API signature:',version)
