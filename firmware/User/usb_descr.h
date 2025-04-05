// https://openatomworkshop.csdn.net/67452de93a01316874d80ac2.html
// 设备描述符
const uint8_t MyDevDescr[] = {
    /*0x12, 0x01, 0x10, 0x01, 0x00, 0x00, 0x00, DevEP0SIZE, 0x3d, 0x41, 0x07, 0x21, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01*/
    0x12,       // bLength
    0x01,       // bDescriptorType (Device)
    0x00, 0x02, // UPDATED bcdUSB 2.0 // 0x10, 0x01,  // bcdUSB 1.1
    0x00,       // bDeviceClass (Use class information in the Interface Descriptors)
    0x00,       // bDeviceSubClass
    0x00,       // bDeviceProtocol
    DevEP0SIZE, // bMaxPacketSize0 64
    0x3D, 0x41, // idVendor 0x413D
    0x07, 0x21, // idProduct 0x2107
    0x00, 0x00, // bcdDevice 0.00
    0x00,       // iManufacturer (String Index)
    0x00,       // iProduct (String Index)
    0x00,       // iSerialNumber (String Index)
    0x01,       // bNumConfigurations 1
    // 18 bytes
};
// 配置描述符
const uint8_t MyCfgDescr[] = {
    /*
    0x09, 0x02, 0x3b, 0x00, 0x02, 0x01, 0x00, 0xA0, 0x32, //配置描述符
    0x09, 0x04, 0x00, 0x00, 0x01, 0x03, 0x01, 0x01, 0x00, //接口描述符,键盘
    0x09, 0x21, 0x11, 0x01, 0x00, 0x01, 0x22, 0x3e, 0x00, //HID类描述符
    0x07, 0x05, 0x81, 0x03, 0x08, 0x00, 0x0a,             //端点描述符
    0x09, 0x04, 0x01, 0x00, 0x01, 0x03, 0x01, 0x02, 0x00, //接口描述符,鼠标
    0x09, 0x21, 0x10, 0x01, 0x00, 0x01, 0x22, 0x34, 0x00, //HID类描述符
    0x07, 0x05, 0x82, 0x03, 0x04, 0x00, 0x0a              //端点描述符
    */
    //配置描述符
    0x09,       //   bLength
    0x02,       //   bDescriptorType (Configuration)
    0x3B, 0x00, //   wTotalLength 59 // 0x3B
    0x02,       //   bNumInterfaces 2
    0x01,       //   bConfigurationValue
    0x00,       //   iConfiguration (String Index)
    0xA0,       //   bmAttributes Remote Wakeup
    0x32,       //   bMaxPower 100mA
    //接口描述符,键盘
    0x09, //   bLength
    0x04, //   bDescriptorType (Interface)
    0x00, //   bInterfaceNumber 0
    0x00, //   bAlternateSetting
    0x01, //   bNumEndpoints 1
    0x03, //   bInterfaceClass
    0x01, //   bInterfaceSubClass
    0x01, //   bInterfaceProtocol, KEYBOARD
    0x00, //   iInterface (String Index)
    //HID类描述符
    0x09,       //   bLength
    0x21,       //   bDescriptorType (HID)
    0x11, 0x01, //   bcdHID 1.11
    0x00,       //   bCountryCode
    0x01,       //   bNumDescriptors
    0x22,       //   bDescriptorType[0] (HID)
    0x39, 0x00, //   wDescriptorLength[0] 62 // UPDATED 0x3E, 0x00
    //端点描述符
    0x07,       //   bLength
    0x05,       //   bDescriptorType (Endpoint)
    0x81,       //   bEndpointAddress (IN/D2H)
    0x03,       //   bmAttributes (Interrupt)
    0x10, 0x00, //   wMaxPacketSize 8 // 0x08, 0x00
    // 0x3a, // 0x01,        //   UPDATED bInterval 1 (unit depends on device speed)
    0x01, //   UPDATED bInterval 1 (unit depends on device speed)
    //接口描述符,鼠标
    0x09, //   bLength
    0x04, //   bDescriptorType (Interface)
    0x01, //   bInterfaceNumber 1
    0x00, //   bAlternateSetting
    0x01, //   bNumEndpoints 1
    0x03, //   bInterfaceClass
    0x01, //   bInterfaceSubClass
    0x02, //   bInterfaceProtocol, MOUSE
    0x00, //   iInterface (String Index)
    //HID类描述符
    0x09,       //   bLength
    0x21,       //   bDescriptorType (HID)
    0x10, 0x01, //   bcdHID 1.10
    0x00,       //   bCountryCode
    0x01,       //   bNumDescriptors
    0x22,       //   bDescriptorType[0] (HID)
    0x34, 0x00, //   wDescriptorLength[0] 52
    //端点描述符
    0x07,       //   bLength
    0x05,       //   bDescriptorType (Endpoint)
    0x82,       //   bEndpointAddress (IN/D2H)
    0x03,       //   bmAttributes (Interrupt)
    0x04, 0x00, //   wMaxPacketSize 4
    0x01,       //   UPDATED bInterval 1 (unit depends on device speed)
    // 0x0a //0x01,        //   UPDATED bInterval 1 (unit depends on device speed)

};
/* USB速度匹配描述符 */
const uint8_t My_QueDescr[] = {
    //0x0A, 0x06, 0x00, 0x02, 0xFF, 0x00, 0xFF, 0x40, 0x01, 0x00
    0x0A,        // bLength
    0x06,        // bDescriptorType (Device Qualifier)
    0x00, 0x02,  // bcdUSB 2.00
    0xFF,        // bDeviceClass
    0x00,        // bDeviceSubClass
    0xFF,        // bDeviceProtocol
    0x40,        // bMaxPacketSize0 64
    0x01,        // bNumConfigurations 1
    0x00,        // bReserved
};

/* USB全速模式,其他速度配置描述符 */
uint8_t USB_FS_OSC_DESC[sizeof(MyCfgDescr)] = {
    0x09, 0x07, /* 其他部分通过程序复制 */
};

// 语言描述符
const uint8_t MyLangDescr[] = {0x04, 0x03, 0x09, 0x04};
// 厂家信息
const uint8_t MyManuInfo[] = {0x0E, 0x03, 'w', 0, 'c', 0, 'h', 0, '.', 0, 'c', 0, 'n', 0};
// 产品信息
const uint8_t MyProdInfo[] = {0x0C, 0x03, 'C', 0, 'H', 0, '5', 0, '7', 0, 'x', 0};
/*HID类报表描述符*/
const uint8_t KeyRepDesc[] = { // NKRO
    /*
    0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x05, 0x07, 0x19, 0xe0, 0x29, 0xe7, 0x15, 0x00, 0x25,
    0x01, 0x75, 0x01, 0x95, 0x08, 0x81, 0x02, 0x95, 0x01, 0x75, 0x08, 0x81, 0x01, 0x95, 0x03,
    0x75, 0x01, 0x05, 0x08, 0x19, 0x01, 0x29, 0x03, 0x91, 0x02, 0x95, 0x05, 0x75, 0x01, 0x91,
    0x01, 0x95, 0x06, 0x75, 0x08, 0x26, 0xff, 0x00, 0x05, 0x07, 0x19, 0x00, 0x29, 0x91, 0x81,
    0x00, 0xC0
    */
    /*
    0x05, 0x01,        // Usage Page (Generic Desktop Ctrls)
    0x09, 0x06,        // Usage (Keyboard)
    0xA1, 0x01,        // Collection (Application)
    0x05, 0x07,        //   Usage Page (Kbrd/Keypad)
    0x19, 0xE0,        //   Usage Minimum (0xE0)
    0x29, 0xE7,        //   Usage Maximum (0xE7)
    0x15, 0x00,        //   Logical Minimum (0)
    0x25, 0x01,        //   Logical Maximum (1)
    0x75, 0x01,        //   Report Size (1)
    0x95, 0x08,        //   Report Count (8)
    0x81, 0x02,        //   Input (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position)
    0x95, 0x01,        //   Report Count (1)
    0x75, 0x08,        //   Report Size (8)
    0x81, 0x01,        //   Input (Const,Array,Abs,No Wrap,Linear,Preferred State,No Null Position)
    0x95, 0x03,        //   Report Count (3)
    0x75, 0x01,        //   Report Size (1)
    0x05, 0x08,        //   Usage Page (LEDs)
    0x19, 0x01,        //   Usage Minimum (Num Lock)
    0x29, 0x03,        //   Usage Maximum (Scroll Lock)
    0x91, 0x02,        //   Output (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position,Non-volatile)
    0x95, 0x05,        //   Report Count (5)
    0x75, 0x01,        //   Report Size (1)
    0x91, 0x01,        //   Output (Const,Array,Abs,No Wrap,Linear,Preferred State,No Null Position,Non-volatile)
    0x95, 0x06,        //   Report Count (6)
    0x75, 0x08,        //   Report Size (8)
    0x26, 0xFF, 0x00,  //   Logical Maximum (255)
    0x05, 0x07,        //   Usage Page (Kbrd/Keypad)
    0x19, 0x00,        //   Usage Minimum (0x00)
    0x29, 0x91,        //   Usage Maximum (0x91)
    0x81, 0x00,        //   Input (Data,Array,Abs,No Wrap,Linear,Preferred State,No Null Position)
    0xC0,              // End Collection
    */
    0x05, 0x01,       //   Usage Page (Generic Desktop),
    0x09, 0x06,       //   Usage (Keyboard),
    0xA1, 0x01,       //   Collection (Application),
    // bitmap of modifiers(功能按键)
    0x05, 0x07,       //   Usage Page (Keyboard),
    0x95, 0x08,       //   Report Count (8),
    0x75, 0x01,       //   Report Size  (1),
    0x15, 0x00,       //   Logical Minimum (0),
    0x25, 0x01,       //   Logical Maximum (1),
    0x19, 0xE0,       //   Usage Minimum (Keyboard LeftControl),
    0x29, 0xE7,       //   Usage Maximum (Keyboard Right GUI),
    0x81, 0x02,       //   Input (Data, Variable, Absolute),
    // bitmap of keys(普通按键)
    0x05, 0x07,       //   Usage Page (Keyboard),
    0x95, 0x78,       //   Report Count (120),
    0x75, 0x01,       //   Report Size  (1),
    0x15, 0x00,       //   Logical Minimum (0),
    0x25, 0x01,       //   Logical Maximum (1),
    0x19, 0x00,       //   Usage Minimum (0),
    0x29, 0x65,       //   Usage Maximum (101),
    0x81, 0x02,       //   Input (Data, Variable, Absolute),
    // LED output report
    0x05, 0x08,       //   Usage Page (LEDs)
    0x95, 0x03,       //   Report Count (3)
    0x75, 0x01,       //   Report Size  (1)
    0x19, 0x01,       //   Usage Minimum (Num Lock   1)
    0x29, 0x03,       //   Usage Maximum (Scroll Lock   3)
    0x91, 0x02,       //   Output (Data,Var,Abs)
    //output凑共1byte(无实际用处)
    0x95, 0x05,       //   Report Count (5)
    0x75, 0x01,       //   Report Size  (1)
    0x91, 0x01,       //   Output (Cnst,Var,Abs)

    0xC0              //   End Collection
};
const uint8_t MouseRepDesc[] = {
    /*
    0x05, 0x01, 0x09, 0x02, 0xA1, 0x01, 0x09, 0x01, 0xA1, 0x00, 0x05, 0x09, 0x19, 0x01, 0x29,
    0x03, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x03, 0x81, 0x02, 0x75, 0x05, 0x95, 0x01,
    0x81, 0x01, 0x05, 0x01, 0x09, 0x30, 0x09, 0x31, 0x09, 0x38, 0x15, 0x81, 0x25, 0x7f, 0x75,
    0x08, 0x95, 0x03, 0x81, 0x06, 0xC0, 0xC0
    */
    0x05, 0x01,        // Usage Page (Generic Desktop Ctrls)
    0x09, 0x02,        // Usage (Mouse)
    0xA1, 0x01,        // Collection (Application)
    0x09, 0x01,        //   Usage (Pointer)
    0xA1, 0x00,        //   Collection (Physical)
    0x05, 0x09,        //     Usage Page (Button)
    0x19, 0x01,        //     Usage Minimum (0x01)
    0x29, 0x03,        //     Usage Maximum (0x03)
    0x15, 0x00,        //     Logical Minimum (0)
    0x25, 0x01,        //     Logical Maximum (1)
    0x75, 0x01,        //     Report Size (1)
    0x95, 0x03,        //     Report Count (3)
    0x81, 0x02,        //     Input (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position)
    0x75, 0x05,        //     Report Size (5)
    0x95, 0x01,        //     Report Count (1)
    0x81, 0x01,        //     Input (Const,Array,Abs,No Wrap,Linear,Preferred State,No Null Position)
    0x05, 0x01,        //     Usage Page (Generic Desktop Ctrls)
    0x09, 0x30,        //     Usage (X)
    0x09, 0x31,        //     Usage (Y)
    0x09, 0x38,        //     Usage (Wheel)
    0x15, 0x81,        //     Logical Minimum (-127)
    0x25, 0x7F,        //     Logical Maximum (127)
    0x75, 0x08,        //     Report Size (8)
    0x95, 0x03,        //     Report Count (3)
    0x81, 0x06,        //     Input (Data,Var,Rel,No Wrap,Linear,Preferred State,No Null Position)
    0xC0,              //   End Collection
    0xC0,              // End Collection
};
