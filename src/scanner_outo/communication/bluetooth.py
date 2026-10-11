from scanner_outo.communication.serial_transport import SerialElmTransport


class BluetoothElmTransport(SerialElmTransport):
    """Bluetooth Classic SPP pela porta COM de saida criada pelo Windows.

    O emparelhamento e feito no Windows; BLE nao usa este transporte.
    """
