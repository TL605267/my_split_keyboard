/********************************** (C) COPYRIGHT *******************************
 * File Name          : Main.c
 * Author             : WCH
 * Version            : V1.1
 * Date               : 2022/01/25
 * Description        : 模拟USB复合设备，键鼠，支持类命令
 *********************************************************************************
 * Copyright (c) 2021 Nanjing Qinheng Microelectronics Co., Ltd.
 * Attention: This software (modified or not) and binary are used for
 * microcontroller manufactured by Nanjing Qinheng Microelectronics.
 *******************************************************************************/

#define DevEP0SIZE 0x40
#define SPI_BUFF_LEN 1
//#define DEBUG 

#include "CH58x_common.h"
#include "keycode.h"
#include "usb_descr.h"
const uint8_t keymap[2][8] = {
    {KC_Q, KC_W, KC_E, KC_R, KC_T, KC_Y, KC_U, KC_I},
    {KC_A, KC_S, KC_D, KC_F, KC_G, KC_H, KC_J, KC_K}
};
/**********************************************************/
uint8_t DevConfig, Ready;
uint8_t SetupReqCode;
uint16_t SetupReqLen;
const uint8_t *pDescr;
uint8_t Report_Value = 0x00;
uint8_t Idle_Value = 0x00;
uint8_t USB_SleepStatus = 0x00; /* USB睡眠状态 */

/*鼠标键盘数据*/
uint8_t HIDMouse[4] = {0x0, 0x0, 0x0, 0x0};
uint8_t HIDKey[16] = {0x0};
/******** 用户自定义分配端点RAM ****************************************/
__attribute__((aligned(4))) uint8_t EP0_Databuf[64 + 64 + 64]; // ep0(64)+ep4_out(64)+ep4_in(64)
__attribute__((aligned(4))) uint8_t EP1_Databuf[64 + 64];      // ep1_out(64)+ep1_in(64)
__attribute__((aligned(4))) uint8_t EP2_Databuf[64 + 64];      // ep2_out(64)+ep2_in(64)
__attribute__((aligned(4))) uint8_t EP3_Databuf[64 + 64];      // ep3_out(64)+ep3_in(64)

// spi
__attribute__((aligned(4))) UINT8 spiBuffrev[SPI_BUFF_LEN];
__attribute__((aligned(4))) UINT8 spiBuffrev_prev[SPI_BUFF_LEN];
const UINT8 all_zero_array[SPI_BUFF_LEN] = {0x0};
uint8_t is_released;
uint8_t row_idx;
/*********************************************************************
 * @fn      USB_DevTransProcess
 *
 * @brief   USB 传输处理函数
 *
 * @return  none
 */
void USB_DevTransProcess(void)
{
    uint8_t len, chtype;
    uint8_t intflag, errflag = 0;

    intflag = R8_USB_INT_FG;
    if (intflag & RB_UIF_TRANSFER)
    {
        if ((R8_USB_INT_ST & MASK_UIS_TOKEN) != MASK_UIS_TOKEN) // 非空闲
        {
            switch (R8_USB_INT_ST & (MASK_UIS_TOKEN | MASK_UIS_ENDP))
            // 分析操作令牌和端点号
            {
            case UIS_TOKEN_IN:
            {
                switch (SetupReqCode)
                {
                case USB_GET_DESCRIPTOR:
                    len = SetupReqLen >= DevEP0SIZE ? DevEP0SIZE : SetupReqLen; // 本次传输长度
                    memcpy(pEP0_DataBuf, pDescr, len);                          /* 加载上传数据 */
                    SetupReqLen -= len;
                    pDescr += len;
                    R8_UEP0_T_LEN = len;
                    R8_UEP0_CTRL ^= RB_UEP_T_TOG; // 翻转
                    break;
                case USB_SET_ADDRESS:
                    R8_USB_DEV_AD = (R8_USB_DEV_AD & RB_UDA_GP_BIT) | SetupReqLen;
                    R8_UEP0_CTRL = UEP_R_RES_ACK | UEP_T_RES_NAK;
                    break;

                case USB_SET_FEATURE:
                    break;

                default:
                    R8_UEP0_T_LEN = 0; // 状态阶段完成中断或者是强制上传0长度数据包结束控制传输
                    R8_UEP0_CTRL = UEP_R_RES_ACK | UEP_T_RES_NAK;
                    break;
                }
            }
            break;

            case UIS_TOKEN_OUT:
            {
                len = R8_USB_RX_LEN;
                if (SetupReqCode == 0x09)
                {
                    PRINT("[%s] Num Lock\t", (pEP0_DataBuf[0] & (1 << 0)) ? "*" : " ");
                    PRINT("[%s] Caps Lock\t", (pEP0_DataBuf[0] & (1 << 1)) ? "*" : " ");
                    PRINT("[%s] Scroll Lock\n", (pEP0_DataBuf[0] & (1 << 2)) ? "*" : " ");
                }
            }
            break;

            case UIS_TOKEN_OUT | 1:
            {
                if (R8_USB_INT_ST & RB_UIS_TOG_OK)
                { // 不同步的数据包将丢弃
                    R8_UEP1_CTRL ^= RB_UEP_R_TOG;
                    len = R8_USB_RX_LEN;
                    DevEP1_OUT_Deal(len);
                }
            }
            break;

            case UIS_TOKEN_IN | 1:
                R8_UEP1_CTRL ^= RB_UEP_T_TOG;
                R8_UEP1_CTRL = (R8_UEP1_CTRL & ~MASK_UEP_T_RES) | UEP_T_RES_NAK;
                break;

            case UIS_TOKEN_OUT | 2:
            {
                if (R8_USB_INT_ST & RB_UIS_TOG_OK)
                { // 不同步的数据包将丢弃
                    R8_UEP2_CTRL ^= RB_UEP_R_TOG;
                    len = R8_USB_RX_LEN;
                    DevEP2_OUT_Deal(len);
                }
            }
            break;

            case UIS_TOKEN_IN | 2:
                R8_UEP2_CTRL ^= RB_UEP_T_TOG;
                R8_UEP2_CTRL = (R8_UEP2_CTRL & ~MASK_UEP_T_RES) | UEP_T_RES_NAK;
                break;

            case UIS_TOKEN_OUT | 3:
            {
                if (R8_USB_INT_ST & RB_UIS_TOG_OK)
                { // 不同步的数据包将丢弃
                    R8_UEP3_CTRL ^= RB_UEP_R_TOG;
                    len = R8_USB_RX_LEN;
                    DevEP3_OUT_Deal(len);
                }
            }
            break;

            case UIS_TOKEN_IN | 3:
                R8_UEP3_CTRL ^= RB_UEP_T_TOG;
                R8_UEP3_CTRL = (R8_UEP3_CTRL & ~MASK_UEP_T_RES) | UEP_T_RES_NAK;
                break;

            case UIS_TOKEN_OUT | 4:
            {
                if (R8_USB_INT_ST & RB_UIS_TOG_OK)
                {
                    R8_UEP4_CTRL ^= RB_UEP_R_TOG;
                    len = R8_USB_RX_LEN;
                    DevEP4_OUT_Deal(len);
                }
            }
            break;

            case UIS_TOKEN_IN | 4:
                R8_UEP4_CTRL ^= RB_UEP_T_TOG;
                R8_UEP4_CTRL = (R8_UEP4_CTRL & ~MASK_UEP_T_RES) | UEP_T_RES_NAK;
                break;

            default:
                break;
            }
            R8_USB_INT_FG = RB_UIF_TRANSFER;
        }
        if (R8_USB_INT_ST & RB_UIS_SETUP_ACT) // Setup包处理
        {
            R8_UEP0_CTRL = RB_UEP_R_TOG | RB_UEP_T_TOG | UEP_R_RES_ACK | UEP_T_RES_NAK;
            SetupReqLen = pSetupReqPak->wLength;
            SetupReqCode = pSetupReqPak->bRequest;
            chtype = pSetupReqPak->bRequestType;

            len = 0;
            errflag = 0;
            if ((pSetupReqPak->bRequestType & USB_REQ_TYP_MASK) != USB_REQ_TYP_STANDARD)
            {
                /* 非标准请求 */
                /* 其它请求,如类请求，产商请求等 */
                if (pSetupReqPak->bRequestType & 0x40)
                {
                    /* 厂商请求 */
                }
                else if (pSetupReqPak->bRequestType & 0x20)
                {
                    switch (SetupReqCode)
                    {
                    case DEF_USB_SET_IDLE: /* 0x0A: SET_IDLE */
                        Idle_Value = EP0_Databuf[3];
                        break; // 这个一定要有

                    case DEF_USB_SET_REPORT: /* 0x09: SET_REPORT */
                        break;

                    case DEF_USB_SET_PROTOCOL: /* 0x0B: SET_PROTOCOL */
                        Report_Value = EP0_Databuf[2];
                        break;

                    case DEF_USB_GET_IDLE: /* 0x02: GET_IDLE */
                        EP0_Databuf[0] = Idle_Value;
                        len = 1;
                        break;

                    case DEF_USB_GET_PROTOCOL: /* 0x03: GET_PROTOCOL */
                        EP0_Databuf[0] = Report_Value;
                        len = 1;
                        break;

                    default:
                        errflag = 0xFF;
                    }
                }
            }
            else /* 标准请求 */
            {
                switch (SetupReqCode)
                {
                case USB_GET_DESCRIPTOR:
                {
                    switch (((pSetupReqPak->wValue) >> 8))
                    {
                    case USB_DESCR_TYP_DEVICE:
                    {
                        pDescr = MyDevDescr;
                        len = MyDevDescr[0];
                    }
                    break;

                    case USB_DESCR_TYP_CONFIG:
                    {
                        pDescr = MyCfgDescr;
                        len = MyCfgDescr[2];
                    }
                    break;

                    case USB_DESCR_TYP_HID:
                        switch ((pSetupReqPak->wIndex) & 0xff)
                        {
                        /* 选择接口 */
                        case 0:
                            pDescr = (uint8_t *)(&MyCfgDescr[18]);
                            len = 9;
                            break;

                        case 1:
                            pDescr = (uint8_t *)(&MyCfgDescr[43]);
                            len = 9;
                            break;

                        default:
                            /* 不支持的字符串描述符 */
                            errflag = 0xff;
                            break;
                        }
                        break;

                    case USB_DESCR_TYP_REPORT:
                    {
                        if (((pSetupReqPak->wIndex) & 0xff) == 0) // 接口0报表描述符
                        {
                            pDescr = KeyRepDesc; // 数据准备上传
                            len = sizeof(KeyRepDesc);
                        }
                        else if (((pSetupReqPak->wIndex) & 0xff) == 1) // 接口1报表描述符
                        {
                            pDescr = MouseRepDesc; // 数据准备上传
                            len = sizeof(MouseRepDesc);
                            Ready = 1; // 如果有更多接口，该标准位应该在最后一个接口配置完成后有效
                        }
                        else
                            len = 0xff; // 本程序只有2个接口，这句话正常不可能执行
                    }
                    break;

                    case USB_DESCR_TYP_STRING:
                    {
                        switch ((pSetupReqPak->wValue) & 0xff)
                        {
                        case 1:
                            pDescr = MyManuInfo;
                            len = MyManuInfo[0];
                            break;
                        case 2:
                            pDescr = MyProdInfo;
                            len = MyProdInfo[0];
                            break;
                        case 0:
                            pDescr = MyLangDescr;
                            len = MyLangDescr[0];
                            break;
                        default:
                            errflag = 0xFF; // 不支持的字符串描述符
                            break;
                        }
                    }
                    break;

                    case USB_DESCR_TYP_QUALIF:
                        pDescr = (uint8_t *)(&My_QueDescr[0]);
                        len = sizeof(My_QueDescr);
                        break;

                    case USB_DESCR_TYP_SPEED:
                        memcpy(&USB_FS_OSC_DESC[2], &MyCfgDescr[2], sizeof(MyCfgDescr) - 2);
                        pDescr = (uint8_t *)(&USB_FS_OSC_DESC[0]);
                        len = sizeof(USB_FS_OSC_DESC);
                        break;

                    default:
                        errflag = 0xff;
                        break;
                    }
                    if (SetupReqLen > len)
                        SetupReqLen = len; // 实际需上传总长度
                    len = (SetupReqLen >= DevEP0SIZE) ? DevEP0SIZE : SetupReqLen;
                    memcpy(pEP0_DataBuf, pDescr, len);
                    pDescr += len;
                }
                break;

                case USB_SET_ADDRESS:
                    SetupReqLen = (pSetupReqPak->wValue) & 0xff;
                    break;

                case USB_GET_CONFIGURATION:
                    pEP0_DataBuf[0] = DevConfig;
                    if (SetupReqLen > 1)
                        SetupReqLen = 1;
                    break;

                case USB_SET_CONFIGURATION:
                    DevConfig = (pSetupReqPak->wValue) & 0xff;
                    break;

                case USB_CLEAR_FEATURE:
                {
                    if ((pSetupReqPak->bRequestType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_ENDP) // 端点
                    {
                        switch ((pSetupReqPak->wIndex) & 0xff)
                        {
                        case 0x83:
                            R8_UEP3_CTRL = (R8_UEP3_CTRL & ~(RB_UEP_T_TOG | MASK_UEP_T_RES)) | UEP_T_RES_NAK;
                            break;
                        case 0x03:
                            R8_UEP3_CTRL = (R8_UEP3_CTRL & ~(RB_UEP_R_TOG | MASK_UEP_R_RES)) | UEP_R_RES_ACK;
                            break;
                        case 0x82:
                            R8_UEP2_CTRL = (R8_UEP2_CTRL & ~(RB_UEP_T_TOG | MASK_UEP_T_RES)) | UEP_T_RES_NAK;
                            break;
                        case 0x02:
                            R8_UEP2_CTRL = (R8_UEP2_CTRL & ~(RB_UEP_R_TOG | MASK_UEP_R_RES)) | UEP_R_RES_ACK;
                            break;
                        case 0x81:
                            R8_UEP1_CTRL = (R8_UEP1_CTRL & ~(RB_UEP_T_TOG | MASK_UEP_T_RES)) | UEP_T_RES_NAK;
                            break;
                        case 0x01:
                            R8_UEP1_CTRL = (R8_UEP1_CTRL & ~(RB_UEP_R_TOG | MASK_UEP_R_RES)) | UEP_R_RES_ACK;
                            break;
                        default:
                            errflag = 0xFF; // 不支持的端点
                            break;
                        }
                    }
                    else if ((pSetupReqPak->bRequestType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_DEVICE)
                    {
                        if (pSetupReqPak->wValue == 1)
                        {
                            USB_SleepStatus &= ~0x01;
                        }
                    }
                    else
                    {
                        errflag = 0xFF;
                    }
                }
                break;

                case USB_SET_FEATURE:
                    if ((pSetupReqPak->bRequestType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_ENDP)
                    {
                        /* 端点 */
                        switch (pSetupReqPak->wIndex)
                        {
                        case 0x83:
                            R8_UEP3_CTRL = (R8_UEP3_CTRL & ~(RB_UEP_T_TOG | MASK_UEP_T_RES)) | UEP_T_RES_STALL;
                            break;
                        case 0x03:
                            R8_UEP3_CTRL = (R8_UEP3_CTRL & ~(RB_UEP_R_TOG | MASK_UEP_R_RES)) | UEP_R_RES_STALL;
                            break;
                        case 0x82:
                            R8_UEP2_CTRL = (R8_UEP2_CTRL & ~(RB_UEP_T_TOG | MASK_UEP_T_RES)) | UEP_T_RES_STALL;
                            break;
                        case 0x02:
                            R8_UEP2_CTRL = (R8_UEP2_CTRL & ~(RB_UEP_R_TOG | MASK_UEP_R_RES)) | UEP_R_RES_STALL;
                            break;
                        case 0x81:
                            R8_UEP1_CTRL = (R8_UEP1_CTRL & ~(RB_UEP_T_TOG | MASK_UEP_T_RES)) | UEP_T_RES_STALL;
                            break;
                        case 0x01:
                            R8_UEP1_CTRL = (R8_UEP1_CTRL & ~(RB_UEP_R_TOG | MASK_UEP_R_RES)) | UEP_R_RES_STALL;
                            break;
                        default:
                            /* 不支持的端点 */
                            errflag = 0xFF; // 不支持的端点
                            break;
                        }
                    }
                    else if ((pSetupReqPak->bRequestType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_DEVICE)
                    {
                        if (pSetupReqPak->wValue == 1)
                        {
                            /* 设置睡眠 */
                            USB_SleepStatus |= 0x01;
                        }
                    }
                    else
                    {
                        errflag = 0xFF;
                    }
                    break;

                case USB_GET_INTERFACE:
                    pEP0_DataBuf[0] = 0x00;
                    if (SetupReqLen > 1)
                        SetupReqLen = 1;
                    break;

                case USB_SET_INTERFACE:
                    break;

                case USB_GET_STATUS:
                    if ((pSetupReqPak->bRequestType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_ENDP)
                    {
                        /* 端点 */
                        pEP0_DataBuf[0] = 0x00;
                        switch (pSetupReqPak->wIndex)
                        {
                        case 0x83:
                            if ((R8_UEP3_CTRL & (RB_UEP_T_TOG | MASK_UEP_T_RES)) == UEP_T_RES_STALL)
                            {
                                pEP0_DataBuf[0] = 0x01;
                            }
                            break;

                        case 0x03:
                            if ((R8_UEP3_CTRL & (RB_UEP_R_TOG | MASK_UEP_R_RES)) == UEP_R_RES_STALL)
                            {
                                pEP0_DataBuf[0] = 0x01;
                            }
                            break;

                        case 0x82:
                            if ((R8_UEP2_CTRL & (RB_UEP_T_TOG | MASK_UEP_T_RES)) == UEP_T_RES_STALL)
                            {
                                pEP0_DataBuf[0] = 0x01;
                            }
                            break;

                        case 0x02:
                            if ((R8_UEP2_CTRL & (RB_UEP_R_TOG | MASK_UEP_R_RES)) == UEP_R_RES_STALL)
                            {
                                pEP0_DataBuf[0] = 0x01;
                            }
                            break;

                        case 0x81:
                            if ((R8_UEP1_CTRL & (RB_UEP_T_TOG | MASK_UEP_T_RES)) == UEP_T_RES_STALL)
                            {
                                pEP0_DataBuf[0] = 0x01;
                            }
                            break;

                        case 0x01:
                            if ((R8_UEP1_CTRL & (RB_UEP_R_TOG | MASK_UEP_R_RES)) == UEP_R_RES_STALL)
                            {
                                pEP0_DataBuf[0] = 0x01;
                            }
                            break;
                        }
                    }
                    else if ((pSetupReqPak->bRequestType & USB_REQ_RECIP_MASK) == USB_REQ_RECIP_DEVICE)
                    {
                        pEP0_DataBuf[0] = 0x00;
                        if (USB_SleepStatus)
                        {
                            pEP0_DataBuf[0] = 0x02;
                        }
                        else
                        {
                            pEP0_DataBuf[0] = 0x00;
                        }
                    }
                    pEP0_DataBuf[1] = 0;
                    if (SetupReqLen >= 2)
                    {
                        SetupReqLen = 2;
                    }
                    break;

                default:
                    errflag = 0xff;
                    break;
                }
            }
            if (errflag == 0xff) // 错误或不支持
            {
                //                  SetupReqCode = 0xFF;
                R8_UEP0_CTRL = RB_UEP_R_TOG | RB_UEP_T_TOG | UEP_R_RES_STALL | UEP_T_RES_STALL; // STALL
            }
            else
            {
                if (chtype & 0x80) // 上传
                {
                    len = (SetupReqLen > DevEP0SIZE) ? DevEP0SIZE : SetupReqLen;
                    SetupReqLen -= len;
                }
                else
                    len = 0; // 下传
                R8_UEP0_T_LEN = len;
                R8_UEP0_CTRL = RB_UEP_R_TOG | RB_UEP_T_TOG | UEP_R_RES_ACK | UEP_T_RES_ACK; // 默认数据包是DATA1
            }

            R8_USB_INT_FG = RB_UIF_TRANSFER;
        }
    }
    else if (intflag & RB_UIF_BUS_RST)
    {
        R8_USB_DEV_AD = 0;
        R8_UEP0_CTRL = UEP_R_RES_ACK | UEP_T_RES_NAK;
        R8_UEP1_CTRL = UEP_R_RES_ACK | UEP_T_RES_NAK;
        R8_UEP2_CTRL = UEP_R_RES_ACK | UEP_T_RES_NAK;
        R8_UEP3_CTRL = UEP_R_RES_ACK | UEP_T_RES_NAK;
        R8_USB_INT_FG = RB_UIF_BUS_RST;
    }
    else if (intflag & RB_UIF_SUSPEND)
    {
        if (R8_USB_MIS_ST & RB_UMS_SUSPEND)
        {
            ;
        } // 挂起
        else
        {
            ;
        } // 唤醒
        R8_USB_INT_FG = RB_UIF_SUSPEND;
    }
    else
    {
        R8_USB_INT_FG = intflag;
    }
}

/*********************************************************************
 * @fn      DevHIDMouseReport
 *
 * @brief   上报鼠标数据
 *
 * @return  none
 */
void DevHIDMouseReport(uint8_t mouse)
{
    HIDMouse[0] = mouse;
    memcpy(pEP2_IN_DataBuf, HIDMouse, sizeof(HIDMouse));
    DevEP2_IN_Deal(sizeof(HIDMouse));
}

/*********************************************************************
 * @fn      DevHIDKeyReport
 *
 * @brief   上报键盘数据
 *
 * @return  none
 */
void DevHIDKeyReport(uint8_t key)
//void DevHIDKeyReport(const void *__restrict, size_t)
{
    //HIDKey[2] = key;
    memcpy(pEP1_IN_DataBuf, HIDKey, sizeof(HIDKey));
    DevEP1_IN_Deal(sizeof(HIDKey));
}

/*********************************************************************
 * @fn      DevWakeup
 *
 * @brief   设备模式唤醒主机
 *
 * @return  none
 */
void DevWakeup(void)
{
    R16_PIN_ANALOG_IE &= ~(RB_PIN_USB_DP_PU);
    R8_UDEV_CTRL |= RB_UD_LOW_SPEED;
    mDelaymS(2);
    R8_UDEV_CTRL &= ~RB_UD_LOW_SPEED;
    R16_PIN_ANALOG_IE |= RB_PIN_USB_DP_PU;
}

/*********************************************************************
 * @fn      DebugInit
 *
 * @brief   调试初始化
 *
 * @return  none
 */
void DebugInit(void)
{
    GPIOA_SetBits(GPIO_Pin_9);
    GPIOA_ModeCfg(GPIO_Pin_8, GPIO_ModeIN_PU);
    GPIOA_ModeCfg(GPIO_Pin_9, GPIO_ModeOut_PP_5mA);
    UART1_DefInit();
}

void RowInit(void)
{
    row_idx = 0;
    GPIOB_ModeCfg(GPIO_Pin_13 | GPIO_Pin_12 | GPIO_Pin_7 | GPIO_Pin_4  , GPIO_ModeOut_PP_5mA);
    GPIOB_ResetBits(GPIO_Pin_10);
    GPIOB_ResetBits(GPIO_Pin_11);
    GPIOB_ResetBits(GPIO_Pin_7);
    GPIOB_ResetBits(GPIO_Pin_4);
}

/*********************************************************************
 * @fn      SPI0_MasterInit
 *
 * @brief   主机模式默认初始化：模式0+3线全双工+8MHz
 *
 * @param   none
 *
 * @return  none
 */
void SPI0_MasterInit() // FIXME
{
    R8_SPI0_CLOCK_DIV = 4; // FIXME 主频时钟8分频
    R8_SPI0_CTRL_MOD = RB_SPI_ALL_CLEAR;
    R8_SPI0_CTRL_MOD = RB_SPI_MOSI_OE | RB_SPI_SCK_OE;
    R8_SPI0_CTRL_CFG |= RB_SPI_AUTO_IF;     // 访问BUFFER/FIFO自动清除IF_BYTE_END标志
    R8_SPI0_CTRL_CFG &= ~RB_SPI_DMA_ENABLE; // 不启动DMA方式
    // set SPI0 pins
    GPIOA_SetBits(GPIO_Pin_12);
    GPIOA_ModeCfg(GPIO_Pin_12 | GPIO_Pin_13 | GPIO_Pin_14, GPIO_ModeOut_PP_5mA);
    GPIOA_ModeCfg(GPIO_Pin_4 | GPIO_Pin_5, GPIO_ModeOut_PP_5mA);
}

/*********************************************************************
 * @fn      main
 *
 * @brief   主函数
 *
 * @return  none
 */
int main()
{
    SetSysClock(CLK_SOURCE_PLL_60MHz);

    DebugInit();
    RowInit();
    PRINT("start\n");
    spiBuffrev_prev[0] = 0;
    #ifdef DEBUG
        GPIOB_ModeCfg(GPIO_Pin_22, GPIO_ModeOut_PP_5mA);
    #endif

    /* 定时器0，设定100ms定时器进行IO口闪灯， PB15-LED */
    TMR0_TimerInit(FREQ_SYS / 10);        // 设置定时时间 10ms
    TMR0_ITCfg(ENABLE, TMR0_3_IT_CYC_END); // 开启中断
    PFIC_EnableIRQ(TMR0_IRQn);

    /* SPI 0 */
    SPI0_MasterInit();
    /*
    spiBuffrev[0] == (UINT8) 0x04;
    is_released = 0;
    */
    pEP0_RAM_Addr = EP0_Databuf;
    pEP1_RAM_Addr = EP1_Databuf;
    pEP2_RAM_Addr = EP2_Databuf;
    pEP3_RAM_Addr = EP3_Databuf;

    USB_DeviceInit();

    PFIC_EnableIRQ(USB_IRQn);
    while (1)
    {
        /*
        mDelaymS(1000);
        //鼠标左键
        DevHIDMouseReport(0x01);
        mDelaymS(100);
        DevHIDMouseReport(0x00);
        mDelaymS(200);
        //键盘按键“wch”
        mDelaymS(1000);
        DevHIDKeyReport(0x1A);
        mDelaymS(100);
        DevHIDKeyReport(0x00);
        mDelaymS(200);
        DevHIDKeyReport(0x06);
        mDelaymS(100);
        DevHIDKeyReport(0x00);
        mDelaymS(200);
        DevHIDKeyReport(0x0B);
        mDelaymS(100);
        DevHIDKeyReport(0x00);
        */
    }
}

/*********************************************************************
 * @fn      DevEP1_OUT_Deal
 *
 * @brief   端点1数据处理
 *
 * @return  none
 */
void DevEP1_OUT_Deal(uint8_t l)
{ /* 用户可自定义 */
    uint8_t i;

    for (i = 0; i < l; i++)
    {
        pEP1_IN_DataBuf[i] = ~pEP1_OUT_DataBuf[i];
    }
    DevEP1_IN_Deal(l);
}

/*********************************************************************
 * @fn      DevEP2_OUT_Deal
 *
 * @brief   端点2数据处理
 *
 * @return  none
 */
void DevEP2_OUT_Deal(uint8_t l)
{ /* 用户可自定义 */
    uint8_t i;

    for (i = 0; i < l; i++)
    {
        pEP2_IN_DataBuf[i] = ~pEP2_OUT_DataBuf[i];
    }
    DevEP2_IN_Deal(l);
}

/*********************************************************************
 * @fn      DevEP3_OUT_Deal
 *
 * @brief   端点3数据处理
 *
 * @return  none
 */
void DevEP3_OUT_Deal(uint8_t l)
{ /* 用户可自定义 */
    uint8_t i;

    for (i = 0; i < l; i++)
    {
        pEP3_IN_DataBuf[i] = ~pEP3_OUT_DataBuf[i];
    }
    DevEP3_IN_Deal(l);
}

/*********************************************************************
 * @fn      DevEP4_OUT_Deal
 *
 * @brief   端点4数据处理
 *
 * @return  none
 */
void DevEP4_OUT_Deal(uint8_t l)
{ /* 用户可自定义 */
    uint8_t i;

    for (i = 0; i < l; i++)
    {
        pEP4_IN_DataBuf[i] = ~pEP4_OUT_DataBuf[i];
    }
    DevEP4_IN_Deal(l);
}

/*********************************************************************
 * @fn      USB_IRQHandler
 *
 * @brief   USB中断函数
 *
 * @return  none
 */
__INTERRUPT
__HIGH_CODE
void USB_IRQHandler(void) /* USB中断服务程序,使用寄存器组1 */
{
    USB_DevTransProcess();
}

/*********************************************************************
 * @fn      TMR0_IRQHandler
 *
 * @brief   TMR0中断函数
 *
 * @return  none
 */
__INTERRUPT
__HIGH_CODE
void TMR0_IRQHandler(void) // TMR0 定时中断
{
    if (TMR0_GetITFlag(TMR0_3_IT_CYC_END))
    {
        TMR0_ClearITFlag(TMR0_3_IT_CYC_END); // 清除中断标志
        key_scan();
    }
}

void key_scan(void)
{
    // FIFO 连续接收
    GPIOA_ResetBits(GPIO_Pin_12); // parallel load
    GPIOA_SetBits(GPIO_Pin_12);   // serial shift
    SPI0_MasterRecv(spiBuffrev, SPI_BUFF_LEN);
    //if (memcmp(spiBuffrev, spiBuffrev_prev, SPI_BUFF_LEN) != 0) // buff != prev, edge
    if ((spiBuffrev[0] & 0x06) != (spiBuffrev_prev[0] & 0x06)) // buff != prev, edge
    {
        //if (memcmp(spiBuffrev, all_zero_array, SPI_BUFF_LEN) == 0) // buff == 0, release
        if ((spiBuffrev[0] & 0x06) == 0x06) // buff == ff, release
        {
            memset(HIDKey, 0, sizeof(HIDKey));
            memcpy(pEP1_IN_DataBuf, HIDKey, sizeof(HIDKey));
            DevEP1_IN_Deal(sizeof(HIDKey));
            #ifdef DEBUG
                GPIOB_SetBits(GPIO_Pin_22);
            #endif
        }
        else // press
        {
            if ((spiBuffrev[0] & (1 << 1)) == 0) {
                HIDKey[2] = 0x01;
                HIDKey[4] = 0x01;
                memcpy(pEP1_IN_DataBuf, HIDKey, sizeof(HIDKey));
                DevEP1_IN_Deal(sizeof(HIDKey));
                #ifdef DEBUG
                    GPIOB_SetBits(GPIO_Pin_22);
                #endif
            }
            if ((spiBuffrev[0] & (1 << 2)) == 0) {
                HIDKey[0] = 0x04;
                memcpy(pEP1_IN_DataBuf, HIDKey, sizeof(HIDKey));
                DevEP1_IN_Deal(sizeof(HIDKey));
            }
        }
        spiBuffrev_prev[0] = spiBuffrev[0];
    }
}