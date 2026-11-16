#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compile actual driver functions with checked host netdev mocks (no kernel headers)."""
from pathlib import Path
import subprocess
import tempfile
r=Path(__file__).resolve().parents[1]/'src'

def function(text,name):
    marker=name+'('
    start=text.index(marker)
    start=text.rfind('\n',0,start)+1
    brace=text.index('{',start)
    depth=1
    end=brace+1
    while depth:
        if text[end]=='{': depth+=1
        elif text[end]=='}': depth-=1
        end+=1
    return text[start:end]+'\n'
h=(r/'fmcs.h').read_text()
n=(r/'fmcs_netdev.c').read_text()
# Find definitions, not the earlier calls/forward declaration.
def definition(text,name):
    import re
    m=re.search(r'^(?:static )?(?:inline )?(?:unsigned int|int|bool|void) '+name+r'\([^;]*?\)\n\{',text,re.M)
    assert m,name
    return function(text[m.start():],name)
source=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdint.h>
#define FMCS_MAX_FTTR_PORTS 16
#define BIT(n) (1U << (n))
#define GENMASK(h,l) (((1U << ((h)+1))-1) & ~((1U << (l))-1))
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define ASSERT_RTNL() ((void)0)
#define rtnl_dereference(x) (x)
#define rcu_assign_pointer(x,v) ((x)=(v))
#define ARPHRD_ETHER 1
#define ETH_MIN_MTU 68
#define VLAN_HLEN 4
struct net_device { int type,mtu,needed_headroom,needed_tailroom,running,carrier,linked,refs; };
struct fmcs_priv { struct net_device *fttr_devs[16]; unsigned char fttr_port_count; struct net_device *fttr_lower; };
struct kernel_param { void *arg; };
static unsigned int port_count=16,routed_offload_mask,bridge_offload_mask,fmcs_bridge_epoch;
static struct fmcs_priv *fmcs_offload_priv;
static int links,unlinks,rx,fail_link=-1,fail_mtu,fail_rx;
#define rtnl_lock() ((void)0)
#define rtnl_unlock() ((void)0)
#define synchronize_net() ((void)0)
#define spin_lock_irqsave(l,f) ((f)=0)
#define spin_unlock_irqrestore(l,f) ((void)(f))
#define netif_running(d) ((d)->running)
#define netif_carrier_ok(d) ((d)->carrier)
#define netif_carrier_on(d) ((d)->carrier=1)
#define netif_carrier_off(d) ((d)->carrier=0)
#define hweight32(x) __builtin_popcount(x)
static int kstrtouint(const char *s,int base,unsigned int *n) {
 char *e; unsigned long v; if (*s=='-') return -EINVAL;
 v=strtoul(s,&e,base); if (*e || v>UINT32_MAX || !*s) return -EINVAL; *n=v; return 0;
}
static int param_set_uint(const char *v,const struct kernel_param *kp) { return kstrtouint(v,0,kp->arg); }
static void nf_flow_table_cleanup(struct net_device *d) { assert(d); }
static void fmcs_bridge_revoke(void) { bridge_offload_mask=0; fmcs_bridge_epoch++; }
static void fmcs_bridge_unbind(struct fmcs_priv *p,struct net_device *d) { assert(p && d); }
static void netdev_rx_handler_unregister(struct net_device *d) { assert(d && rx); rx=0; }
static void netdev_upper_dev_unlink(struct net_device *l,struct net_device *d) { assert(l && d && d->linked); d->linked=0; unlinks++; }
static int netdev_upper_dev_link(struct net_device *l,struct net_device *d,void *v) { assert(l && d && !d->linked); if (links==fail_link) return -EIO; d->linked=1; links++; return 0; }
static int dev_set_mtu(struct net_device *d,int mtu) { assert(d); if (fail_mtu) return -EIO; d->mtu=mtu; return 0; }
#define fmcs_handle_frame NULL
static int netdev_rx_handler_register(struct net_device *d,void *f,struct fmcs_priv *p) { assert(d && p && !rx); if(fail_rx) return -EIO; rx=1; return 0; }
static void dev_hold(struct net_device *d) { d->refs++; }
static void dev_put(struct net_device *d) { assert(d->refs>0); d->refs--; }
'''
for name in ['fmcs_fttr_port_valid','fmcs_fttr_port_mask']:
    source+=definition(h.replace('static inline','static'),name)
for name in ['fmcs_port_count_set','fmcs_offload_cleanup','fmcs_offload_mask_set','fmcs_bridge_mask_set','fmcs_bridge_port_enabled','fmcs_bridge_pair_enabled','fmcs_fttr_set_carrier','fmcs_lower_unlink','fmcs_lower_link','fmcs_netdevs_validate_params']:
    source+=definition(n,name)
source+=r'''
int main(void) {
 struct net_device ds[16],lower;
 struct fmcs_priv p;
 struct kernel_param kp={.arg=&port_count};
 const unsigned int counts[]={0,1,4,16};
 assert(fmcs_port_count_set("17",&kp)==-EINVAL);
 assert(fmcs_port_count_set("-1",&kp)==-EINVAL);
 assert(fmcs_port_count_set("garbage",&kp)==-EINVAL);
 for (int t=0;t<4;t++) {
  unsigned int count=counts[t],mask=(1U<<count)-1;
  memset(&p,0,sizeof(p)); memset(ds,0,sizeof(ds)); memset(&lower,0,sizeof(lower));
  p.fttr_port_count=count; lower.type=ARPHRD_ETHER; lower.mtu=1500;
  for (unsigned int i=0;i<count;i++) { p.fttr_devs[i]=&ds[i]; ds[i].mtu=1600; ds[i].running=ds[i].carrier=1; }
  assert(fmcs_fttr_port_mask(count)==mask);
  char number[16]; snprintf(number,sizeof(number),"%u",count);
  assert(!fmcs_port_count_set(number,&kp));
  routed_offload_mask=bridge_offload_mask=0;
  assert(!fmcs_netdevs_validate_params());
  routed_offload_mask=BIT(count);
  assert(fmcs_netdevs_validate_params()==-EINVAL); routed_offload_mask=0;
  fmcs_offload_priv=&p;
  assert(fmcs_offload_mask_set("0x10000",&kp)==-EINVAL);
  snprintf(number,sizeof(number),"%u",BIT(count));
  assert(fmcs_offload_mask_set(number,&kp)==-EINVAL);
  snprintf(number,sizeof(number),"%u",mask);
  assert(!fmcs_offload_mask_set(number,&kp));
  if(count>1) assert(!fmcs_bridge_mask_set(number,&kp));
  else assert(!fmcs_bridge_mask_set("0",&kp));
  assert(!fmcs_fttr_port_valid(&p,0)); assert(!fmcs_fttr_port_valid(&p,count+1));
  assert(!fmcs_fttr_port_valid(&p,UINT32_MAX));
  assert(!fmcs_bridge_port_enabled(&p,0)); assert(!fmcs_bridge_port_enabled(&p,count+1));
  assert(!fmcs_bridge_pair_enabled(&p,UINT32_MAX,0));
  assert(fmcs_fttr_set_carrier(&p,0,1)==-EINVAL);
  assert(fmcs_fttr_set_carrier(&p,count+1,1)==-EINVAL);
  if(count) { assert(!fmcs_fttr_set_carrier(&p,count,0)); assert(!ds[count-1].carrier); ds[count-1].carrier=1; }
  links=unlinks=rx=0; fail_link=-1; fail_mtu=fail_rx=0;
  assert(!fmcs_lower_link(&p,&lower)); assert(links==(int)count && rx && lower.refs==1);
  for(unsigned int i=0;i<count;i++) assert(ds[i].mtu==1500);
  fmcs_lower_unlink(&p); assert(unlinks==(int)count && !rx && !lower.refs && !p.fttr_lower);
  fmcs_lower_unlink(&p);
  fail_rx=1; links=unlinks=0;
  assert(fmcs_lower_link(&p,&lower)==-EIO); assert(links==unlinks && !rx && !p.fttr_lower); fail_rx=0;
  if(count) {
   links=unlinks=0; fail_link=count/2;
   assert(fmcs_lower_link(&p,&lower)==-EIO); assert(links==unlinks); fail_link=-1;
   links=unlinks=0; fail_mtu=1; ds[count-1].mtu=1600;
   assert(fmcs_lower_link(&p,&lower)==-EIO); assert(links==unlinks); fail_mtu=0;
   links=unlinks=0; p.fttr_devs[count-1]=NULL;
   assert(fmcs_lower_link(&p,&lower)==-EINVAL); assert(links==unlinks);
   assert(!fmcs_bridge_pair_enabled(&p,1,count));
   assert(fmcs_fttr_set_carrier(&p,count,1)==-EINVAL);
  }
  printf("PASS actual driver functions count=%u\n",count);
 }
 port_count=17; assert(fmcs_netdevs_validate_params()==-EINVAL);
 assert(!fmcs_fttr_port_mask(17));
 puts("driver host tests passed");
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='fmcs-driver-test-') as d:
    c=Path(d)/'ports-test.c'; c.write_text(source)
    executable=Path(d)/'ports-test'
    subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Wno-unused-parameter','-Werror','-fsanitize=address,undefined','-g',str(c),'-o',str(executable)],check=True)
    subprocess.run([str(executable)],check=True)
