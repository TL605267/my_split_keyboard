# My split keyboard firmware

## Overview
This folder contains the firmware for my split keyboard. The firmware is based on [ch583evt_gcc_makefile template from cjacker](https://github.com/cjacker/ch583evt_gcc_makefile). The keyboard scanning code is placed in ./User folder. 

## Features
- **NKRO**: Brief description.
- **Fast Key Scanning**: Brief description.
- **Layers (WIP)**: Brief description.

## Getting Started

### Prerequisites
Before using this firmware, ensure you have the following installed:
- riscv-none-embed-gcc toolchain
- [wchisp](https://github.com/ch32-rs/wchisp)

### Installation
```bash
git clone https://github.com/TL605267/my_split_keyboard.git
```

### Program CH582
```bash
make isp
```