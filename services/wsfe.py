from datetime import datetime
import uuid

class Wsfe:
    """
    Clase simulada para la generación de comprobantes electrónicos (Factura).
    Permite emitir una factura simple con datos del cliente, productos y totales.
    """

    def __init__(self):
        self.comprobantes_emitidos = []

    def generar_factura(self, cliente_nombre, carrito):
        """
        Genera un comprobante electrónico con los productos del carrito.
        """
        if not carrito.productos:
            return "El carrito está vacío. No se puede generar la factura."

        numero_factura = f"F-{uuid.uuid4().hex[:8].upper()}"
        fecha_emision = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        productos_detalle = [
            {
                "nombre": p.nombre,
                "precio_unitario": p.precio,
                "descuento": p.descuento,
                "precio_final": p.obtener_precio_final()
            }
            for p in carrito.productos
        ]

        total = carrito.obtener_total()

        comprobante = {
            "nro_factura": numero_factura,
            "fecha": fecha_emision,
            "cliente": cliente_nombre,
            "detalle_productos": productos_detalle,
            "total": total
        }

        self.comprobantes_emitidos.append(comprobante)
        return comprobante

    def mostrar_historial(self):
        """
        Devuelve el historial de comprobantes emitidos.
        """
        return self.comprobantes_emitidos
