import os
import re
from collections import deque
from nicegui import ui, app
from pathlib import Path
from binary_tree import BinaryTree
from supabase import create_client, Client
from services.supabase_service import get_products_from_supabase 
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib
from weasyprint import HTML
from products import Product, DiscountedProduct, BaseProduct 
import traceback
from datetime import datetime
from dotenv import load_dotenv


productsContainer = None #VISA
cartContainer = None
searchField = None
products = deque() 
cart = [] 
last_purchase = None 


app.add_static_files('/img', Path(__file__).parent / 'img')
ui.add_head_html('<title>Perfumería TripleC</title>')


load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
smtp_email = os.getenv('SMTP_EMAIL')
smtp_pass = os.getenv('SMTP_PASSWORD')
smtp_host = os.getenv('SMTP_HOST')
smtp_port = int(os.getenv('SMTP_PORT'))


supabase: Client = create_client(url, key) 


# --- Funciones de Carrito ---
def check_stock(product, size):


    pass


def addToCart(product):
    selected_capacity = product.getSelectedCapacity()
    
    found_in_cart = False
    for item in cart:
        if item['product'].id == product.id and item['capacity'] == selected_capacity:
            item['quantity'] += 1
            found_in_cart = True
            break
    if not found_in_cart:
        cart.append({
            'product': product,
            'capacity': selected_capacity,
            'quantity': 1,
        })
    ui.notify(f'Agregado al carrito: {product.getName()} ({selected_capacity} ml)', duration=2, type='positive')
    if cartContainer:
        updateCart()


def removeOneFromCart(item_to_remove):
    for i, item in enumerate(cart):
        if item['product'].id == item_to_remove['product'].id and item['capacity'] == item_to_remove['capacity']:
            if item['quantity'] > 1:
                item['quantity'] -= 1
                ui.notify(f'Un artículo eliminado del carrito: {item["product"].getName()} ({item["capacity"]} ml)', duration=2)
            else:
                cart.pop(i)
                ui.notify(f"Eliminado del carrito: {item['product'].getName()} ({item['capacity']} ml)", duration=2, type='info')
            break
    if cartContainer:
        updateCart()


def updateCart():
    if cartContainer is None:
        return
    arbol_carrito = BinaryTree()
    for item in cart:
        arbol_carrito.agregar(item)
    productos_ordenados = arbol_carrito.recorrido_in_order()
    total = 0
    
    # Calcular costo de envío (ejemplo básico)
    shipping_cost = 10 if any(item['quantity'] > 0 for item in cart) else 0  # $15.00 si hay productos
    
    # Mostrar el subtotal, envío y total
    with cartContainer:
        ui.separator()
        ui.label(f'Subtotal: ${total:.2f}').style('text-align: right;')
        
    with cartContainer: 
        cartContainer.clear()
        for item in productos_ordenados:
            product = item['product']
            capacity = item['capacity']
            quantity = item['quantity']
            price = product.getPriceForCapacity(capacity)
            total += price * quantity
            with ui.row().style('align-items: center; width: 100%; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #eee;'):
                ui.label(f"{product.getName()} ({capacity} ml) - Cantidad: {quantity}").style('flex-grow: 1;')
                ui.label(f"Precio: ${price * quantity:.2f}").style('min-width: 100px; text-align: right; margin-right: 10px;')
                ui.button('X', on_click=lambda i=item: removeOneFromCart(i)).props('flat round color=negative').style('margin-left: 5px;')
        ui.separator().classes('my-2')
        ui.label(f'Envío: ${shipping_cost:.2f}').style('text-align: right;')
        ui.label(f'Total: ${total+ shipping_cost:.2f}').style('font-weight: bold; font-size: 1.2em; text-align: center; width: 100%;')
    cartContainer.update()


def processProducts(data): 
    products_deque = deque()
    for product_data in data:
        if 'descuento' in product_data and product_data['descuento'] > 0:
            products_deque.append(DiscountedProduct(
                product_data['id'],
                product_data['nombrePerfume'],
                product_data['marcaPerfume'], 
                product_data['aromaPerfume'],  
                product_data['duracionPerfume'], 
                product_data['precioPerfume'],
                product_data['imagenPerfume'],
                product_data['descuento']
            ))
        else:
            products_deque.append(Product(
                product_data['id'],
                product_data['nombrePerfume'],
                product_data['marcaPerfume'], 
                product_data['aromaPerfume'], 
                product_data['duracionPerfume'], 
                product_data['precioPerfume'],
                product_data['imagenPerfume']
            ))
    return products_deque


def searchProducts(searchTerm):
    global products
    if not searchTerm:
        return list(products)
    searchTerm = searchTerm.lower()
    return [product for product in products if searchTerm in product.getName().lower()]


def onSearchButtonClick(searchField_ui):
    searchTerm = searchField_ui.value
    filteredProducts = searchProducts(searchTerm)
    showProducts(productsContainer, filteredProducts)


def onResetButtonClick():
    global searchField
    if searchField:
        searchField.value = ""
    showProducts(productsContainer, list(products))


def showProducts(container, products_to_show):
    container.clear() 
    if not products_to_show:
        ui.notify('No hay productos disponibles', duration=3)
    else:
        for product in products_to_show:
            with container:
                with ui.card().style('margin: 15px; width: 220px; box-shadow: 2px 4px 8px rgba(0, 0, 0, 0.1); border-radius: 12px;'):
                    with ui.column().style('align-items: center; padding: 10px;'):
                        ui.image(product.getImageUrl()).style('width: 150px; height: 150px; border-radius: 10px; object-fit: cover;')
                        ui.label(f"{product.getName()}").style('font-weight: bold; font-size: 18px; text-align: center; margin-top: 10px;')
                        ui.label(f"Marca:  {product.getBrand()}").style('font-size: 12px; text-align: center; margin-top: 10px;')
                        ui.label(f"Aroma:  {product.getScent()}").style('font-size: 12px; text-align: center; margin-top: 10px;') 
                        ui.label(f"Duracion:  {product.getDuration()}").style('font-size: 12px; text-align: center; margin-top: 10px;') 
                        with ui.row().style('justify-content: center; margin: 10px 0;'):
                            ui.label('Capacidad:')
                            ui.select(
                                [50, 70, 100],
                                value=product.getSelectedCapacity(),
                                on_change=lambda e, p=product: (p.setSelectedCapacity(e.value), showProducts(productsContainer, list(products)))
                            ).style('margin-left: 5px; width: 100px;')
                        price = product.getPriceForCapacity(product.getSelectedCapacity())
                        if isinstance(product, DiscountedProduct):
                            original_base_price_for_capacity = BaseProduct.getPriceForCapacity(product, product.getSelectedCapacity())
                            originalPriceDisplay = original_base_price_for_capacity / (1 - product.discount / 100) if product.discount > 0 else original_base_price_for_capacity
                            ui.label(f'Precio de lista: ${originalPriceDisplay:.2f}').style('text-decoration: line-through; color: red; text-align: center; font-size: 16px;')
                            ui.label(f'Precio de oferta: ${price:.2f}').style('color: green; text-align: center; font-size: 16px; font-weight: bold;')
                        else:
                            ui.label(f'Precio: ${price:.2f}').style('color: green; text-align: center; font-size: 16px; font-weight: bold;')
                        ui.button('Agregar al carrito', on_click=lambda p=product: addToCart(p)).style('background-color: #FF9800; color: white; margin-top: 10px; width: 100%;').classes('rounded-md')


def loadProducts(container, order='asc', filtro = None):
    global products
    data = get_products_from_supabase()
    if not data:
        ui.notify('No se pudieron cargar los productos. Intenta de nuevo más tarde.', duration=3, type='negative')
        products = deque()
        showProducts(container, list(products))
        return
    products = processProducts(data)
    if filtro:


        if 'brand' in filtro:
            products = [p for p in products if p.getBrand() == filtro['brand']]
        elif 'scent' in filtro:
            products = [p for p in products if p.getScent() == filtro['scent']]
        elif 'duration' in filtro:
            products = [p for p in products if p.getDuration() == filtro['duration']]


    products = deque(sorted(list(products), key=lambda p: p.getPrice(), reverse=(order == 'desc')))
    showProducts(container, list(products))


marcaCombo = {'combo': None, 'select': None}
aromaCombo = {'combo': None, 'select': None}
duracionCombo = {'combo': None, 'select': None}
visibleEstado = {'marca': False,'aroma': False,'duracion': False,}


def initCombos():
    global marcaCombo, aromaCombo, duracionCombo


    with ui.column():
        with ui.row().classes('items-center q-gutter-sm').style('display: none; position: absolute; left: 410px; top: 315px;') as marca:
            ui.label('Elegir Marca')
            marcaSelect = ui.select(
                options=[
                    'Armani', 'Boss', 'Bvlgari', 'Chanel', 'Chloe', 'Creed',
                    'Dolce Gabbana', 'Dior', 'Givenchy', 'Gucci', 'Hermes',
                    'Jean Paul Gaultier', 'Lancome', 'Marc Jacobs', 'Marvel',
                    'Montblanc', 'Mujercitas', 'PACO', 'Paco Rabanne', 'Prada',
                    'Shakira', 'Tom Ford', 'Versace', 'Viktor and Rolf', 'Yves Saint Laurent'
                ],
                on_change=lambda e: loadProducts(productsContainer, filtro={'brand': e.value})
            )
            marcaCombo.update({'combo': marca, 'select': marcaSelect})


        with ui.row().classes('items-center q-gutter-sm').style('display: none; position: absolute; left: 520px; top: 315px;') as aroma:
            ui.label('Elegir Aroma')
            aromaSelect = ui.select(
                options=['Amaderada', 'Chipre', 'Citrico', 'Floral', 'Gourmand', 'Oriental'],
                on_change=lambda e: loadProducts(productsContainer, filtro={'scent': e.value})
            )
            aromaCombo.update({'combo': aroma, 'select': aromaSelect})


        with ui.row().classes('items-center q-gutter-sm').style('display: none; position: absolute; left: 640px; top: 315px;') as duracion:
            ui.label('Elegir Duración')
            duracionSelect = ui.select(
                options=['Volátil', 'Ligero', 'Persistente', 'Longevo'],
                on_change=lambda e: loadProducts(productsContainer, filtro={'duration': e.value})
            )
            duracionCombo.update({'combo': duracion, 'select': duracionSelect})




comboActivo = {'actual': None}
def closeCombo():
    global visibleEstado
    if comboActivo['actual'] == marcaCombo['combo']:
        marcaCombo['combo'].style('display: none')
        visibleEstado['marca'] = False
    elif comboActivo['actual'] == aromaCombo['combo']:
        aromaCombo['combo'].style('display: none')
        visibleEstado['aroma'] = False
    elif comboActivo['actual'] == duracionCombo['combo']:
        duracionCombo['combo'].style('display: none')
        visibleEstado['duracion'] = False
    comboActivo['actual'] = None


def toggleMarca():
    global visibleEstado
    if not visibleEstado['marca']:
        closeCombo()
        marcaCombo['combo'].style('display: flex')
        visibleEstado['marca'] = True
        comboActivo['actual'] = marcaCombo['combo']
    else:
        marcaCombo['combo'].style('display: none')
        visibleEstado['marca'] = False
        comboActivo['actual'] = None


def toggleAroma():
    global visibleEstado
    if not visibleEstado['aroma']:
        closeCombo()
        aromaCombo['combo'].style('display: flex')
        visibleEstado['aroma'] = True
        comboActivo['actual'] = aromaCombo['combo']
    else:
        aromaCombo['combo'].style('display: none')
        visibleEstado['aroma'] = False
        comboActivo['actual'] = None


def toggleDuracion():
    global visibleEstado
    if not visibleEstado['duracion']:
        closeCombo()
        duracionCombo['combo'].style('display: flex')
        visibleEstado['duracion'] = True
        comboActivo['actual'] = duracionCombo['combo']
    else:
        duracionCombo['combo'].style('display: none')
        visibleEstado['duracion'] = False
        comboActivo['actual'] = None




def logout():
    try:
        ui.notify('Sesión cerrada con éxito', type='info')
        app.storage.user.clear() 
        ui.navigate.to('/')
    except Exception as e:
        ui.notify(f"Error al cerrar sesión: {e}", type='negative')
        print(f"Error during logout: {e}")


async def registrar(email_input, password_input, nombre_input, apellido_input, direccion_input):
    email = email_input.value
    password = password_input.value
    nombre = nombre_input.value
    apellido = apellido_input.value
    direccion = direccion_input.value


    if not all([email, password, nombre, apellido, direccion]):
        ui.notify("Todos los campos son requeridos", type="warning")
        return 
    if not validate_email(email):
        ui.notify("Email no válido", type="warning")
        return
    
    if not validate_direccion(direccion):
        ui.notify("Dirección no válida", type="warning")
        return


    try:
        # Registrar al usuario en Supabase Auth
        response = supabase.auth.sign_up({"email": email, "password": password})
        
        if response and response.user:
            user_id = response.user.id 
            user_email = response.user.email




            try:
                insert_response = supabase.table('users').insert({
                    'id': user_id,
                    'email': user_email,
                    'nombre': nombre,
                    'apellido': apellido,
                    'direccion': direccion,
                    'puntos': 0,
                    'rol': 'cliente',
                }).execute()


                if insert_response.data and len(insert_response.data) > 0:
                    ui.notify("¡Registro exitoso! Por favor, verifica tu correo.", type="positive")
                    ui.navigate.to('/') 
                else:
                    ui.notify(f"Error al guardar datos adicionales: {insert_response.get('message', 'Error desconocido en la base de datos.')}", type="negative")
                    print(f"Error inserting user additional data: {insert_response}")


            except Exception as e:


                if "duplicate key value violates unique constraint" in str(e):
                    ui.notify("El email ya está registrado. Por favor, inicia sesión o restablece tu contraseña.", type="warning")
                    print(f"Duplicate email registration attempt: {email}")
                else:
                    ui.notify(f"Error al guardar datos adicionales de usuario: {e}", type="negative")
                    print(f"Error inserting user profile after auth signup: {e}")
                    traceback.print_exc()


        else:
            ui.notify("No se pudo registrar. Revisa los datos ingresados.", type="negative")
    except Exception as e:
        ui.notify(f"Error inesperado al registrar: {e}", type="negative")
        traceback.print_exc() 
        print(f"Unexpected error during registration: {e}")




async def login(username_input, password_input, rol_input):
    username = username_input.value
    password = password_input.value
    if not username or not password:
        ui.notify("Usuario y contraseña requeridos", type="warning")
        return
    try:
        response = supabase.auth.sign_in_with_password({"email": username, "password": password})
        if response and response.user:
            app.storage.user['id'] = response.user.id 
            app.storage.user['email'] = response.user.email 


            # Obtener el rol del usuario en la base de datos
            user_id = response.user.id
            user_data = supabase.table('users').select('rol').eq('id', user_id).single().execute()
            rol_bd = user_data.data['rol'] if user_data.data else None
            rol_seleccionado = rol_input.value


            rol_valido = False


            if rol_bd == rol_seleccionado:
                rol_valido = True
            elif rol_seleccionado == 'cliente' and rol_bd in ['administrador', 'analista de marketing']:
                rol_valido = True


            if not rol_valido:
                ui.notify("Rol incorrecto. Verifica tu rol seleccionado.", type="negative")
                return


            ui.notify("¡Inicio de sesión exitoso!", type="positive")


            if rol_seleccionado == 'cliente':
                ui.navigate.to('/products')
            elif rol_seleccionado == 'administrador':
                ui.navigate.to('/admin')
            elif rol_seleccionado == 'analista de marketing':
                ui.navigate.to('/marketing')


        else:
            ui.notify("Error al iniciar sesión. Verifica tus credenciales.", type="negative")
    except Exception as e:
        ui.notify(f"Error inesperado al iniciar sesión: {e}", type='negative')
        print(f"Unexpected error during login: {e}")


async def reset_password_email(email_input_dialog, dialog):
    email = email_input_dialog.value
    if not email or not validate_email(email):
        ui.notify("Por favor, ingresa un email válido.", type="warning")
        return
    try:
        supabase.auth.reset_password_for_email(email)
        ui.notify("Si el email existe, se ha enviado un enlace de restablecimiento. Revisa tu bandeja de entrada.", type="positive", duration=5)
        dialog.close() 
    except Exception as e:
        ui.notify(f"Error al enviar el enlace de restablecimiento: {e}", type="negative")
        print(f"Error during password reset email send: {e}")




def validate_email(email):
    """Validate the email format using a regex."""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None


def validate_direccion(direccion):
    """Valida una dirección típica de Buenos Aires."""
    direccion_regex = r"^(Av\.|Avenida|Calle|Ruta)?\s?[A-ZÁÉÍÓÚÑa-záéíóúñ0-9\s'.-]{3,}\s\d{1,5}(?:\s?(Piso|Depto|Dpto|PB|1|2|3|[a-zA-Z0-9]+)?\s?[a-zA-Z0-9]*)?$"
    return re.match(direccion_regex, direccion) is not None


async def get_users_from_supabase():
    try:
        response = supabase.table('users').select('id, puntos, email').execute()
        if response.data:
            return response.data
        else:
            return []
    except Exception as e:
        ui.notify(f'Error al cargar usuarios: {e}', type='negative')
        print(f'Error fetching users: {e}')
        return []


# --- Main   ---
@ui.page('/')
def home_page():
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} </style> <title>Perfumería TripleC</title>""")

    with ui.column().classes('w-full'):

        # Encabezado con logo y botones
        with ui.row().classes('w-full items-center justify-between p-4 border border-black bg-white'):
            ui.image('/img/logo_triplec.png').on('click', lambda: ui.navigate.to('/')).style('height: 100px; width: 200px; object-fit: contain;').classes('cursor-pointer')

            with ui.row().classes('gap-4'):
                ui.button('Registro', on_click=lambda: ui.navigate.to('/registro')).classes('bg-blue-600 border border-black text-white')
                ui.button('Login', on_click=lambda: ui.navigate.to('/login')).classes('bg-blue-600 border border-black text-white')
        
        with ui.row().classes('w-full items-center justify-between p-2 border border-black bg-white'):
            with ui.row().classes('gap-6'):
                ui.button('Productos', on_click=lambda: ui.navigate.to('/products')).classes('bg-blue-600 border-none text-white')
                ui.button('Promociones', on_click=lambda: ui.navigate.to('/promotions')).classes('bg-blue-600 border-none text-white')
            ui.label('¡SALE! - Descuentos imperdibles, solo por tiempo limitado. HASTA un 40% OFF en productos seleccionados').classes('text-sm')
    
        total_slides = 3
        current_slide = {'index': 0}

        def prev_slide_local():
            current_slide['index'] = (current_slide['index'] - 1 + total_slides) % total_slides
            carousel.set_value(f'slide_{current_slide["index"] + 1}')

        def next_slide_local():
            current_slide['index'] = (current_slide['index'] + 1) % total_slides
            carousel.set_value(f'slide_{current_slide["index"] + 1}')
 
        with ui.row().classes('items-center w-full justify-between').style('height: 745px; position: relative;'):
            
            ui.button('', on_click=prev_slide_local)\
                .props('flat round icon=arrow_left')\
                .classes('text-3xl w-16 h-16 bg-white shadow-md rounded-full hover:bg-blue-100 transition duration-300 z-10')\
                .style('position: absolute; left: 20px; top: 50%; transform: translateY(-50%);')
            
            # Carrusel
            with ui.card().classes('grow border border-black shadow-lg overflow-hidden').style('height: 100%; border-radius: 20px;'):
                carousel = ui.carousel().classes('w-full h-full')
                with carousel:
                    with ui.carousel_slide('slide_1').style('height: 100%'):
                        ui.image('/img/banner-triplec.png').classes('w-full h-full object-contain block')
                    with ui.carousel_slide('slide_2').style('height: 100%'):
                        ui.image('/img/perfumes3.png').classes('w-full h-full object-contain block')
                    with ui.carousel_slide('slide_3').style('height: 100%'):
                        ui.image('/img/lightblue.png').classes('w-full h-full object-contain block')
                carousel.set_value('slide_1')
     
            ui.button('', on_click=next_slide_local)\
                .props('flat round icon=arrow_right')\
                .classes('text-3xl w-16 h-16 bg-white shadow-md rounded-full hover:bg-blue-100 transition duration-300 z-10')\
                .style('position: absolute; right: 20px; top: 50%; transform: translateY(-50%);')
     
        with ui.row().classes('items-center justify-between w-full').style('height: 700px;'):
            ui.button('').props('flat').classes('w-16 h-16 opacity-0')
            with ui.card().classes('grow border border-black shadow-lg overflow-hidden').style('height: 100%; border-radius: 20px;'):
                ui.image('/img/tripleC.png').classes('h-full w-full object-cover')
            ui.button('').props('flat').classes('w-16 h-16 opacity-0')

        # Footer superior
        with ui.row().style('width: 100%; background-color: #f1f1f1; padding: 20px; margin-top: 10px; border: 1px solid black;'):
            ui.label('Compra 100% Segura. Perfumería Triple C garantiza la seguridad transaccional de sus clientes.').style('flex-grow: 1; text-align: left;')
            ui.label('CUIT: 01-34567890-1 - Calle 1234, CABA.').style('flex-grow: 1; text-align: right;')

        # Footer inferior
        with ui.row().style('width: 100%; background-color: #f1f1f1; padding: 20px; margin-top: 10px; border: 1px solid black;'):
            ui.label('© 2023 Triple C. Todos los derechos reservados.').style('flex-grow: 1; text-align: left;')
            ui.link('Política de Privacidad', '/privacy').style('margin-right: 20px;')
            ui.link('Términos de Servicio', '/terms').style('margin-right: 20px;')
            ui.link('Contacto', '/contacts').style('margin-right: 5px;')


@ui.page('/login') 
def login_register_page():
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} </style>""")
    global cart
    cart.clear() 
    with ui.column().classes('absolute-center items-center'):
        ui.link('Iniciar Sesión', target='/').style('font-size: 28px; font-weight: bold; margin-bottom: 15px; color: white; text-align: center; width: 100%; text-decoration: none;')
        with ui.card().classes('w-96 p-4 shadow-lg'):

            username_input = ui.input('Usuario').classes('w-full mb-3').props('outlined') 
            password_input = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full mb-4').props('outlined')

            rol_input = ui.select(
                options=['cliente', 'administrador', 'analista de marketing'],
                label='Seleccionar Rol',
                value='cliente' 
            ).classes('w-full mb-4')

            with ui.row().classes('w-full justify-center'):
                with ui.dialog() as reset_dialog, ui.card():
                    ui.label("Restablecer Contraseña").classes("text-xl font-bold mb-4")
                    email_input_dialog = ui.input('Correo electrónico registrado').props('type=email outlined').classes('w-full mb-4')
                    ui.button('Enviar enlace de restablecimiento', on_click=lambda: reset_password_email(email_input_dialog, reset_dialog)).classes('w-full bg-blue-600 text-white').props('push')
                    ui.button('Cancelar', on_click=reset_dialog.close).classes('w-full mt-2').props('flat')

                ui.button('¿Olvidaste tu contraseña?', on_click=reset_dialog.open).props('flat color=warning').style('margin-top: 5px; font-size: 14px;')
           
            ui.button('Ingresar', on_click=lambda: login(username_input, password_input, rol_input)).classes('w-full bg-blue-600 text-white').props('push')
            ui.separator().classes('my-4')
            ui.button('Registrarse', on_click=lambda: ui.navigate.to('/registro')).classes('w-full bg-green-600 text-white').props('push')


@ui.page('/registro')
def registro_page():
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} </style>""")
    with ui.column().classes('absolute-center items-center'):
        ui.link('Crear Cuenta', target='/').style('font-size: 28px; font-weight: bold; margin-bottom: 20px; color: white; text-decoration: none;')
        with ui.card().classes('w-96 p-4 shadow-lg'):
            email_input = ui.input('Correo electrónico').props('type=email').classes('w-full mb-3').props('outlined')
            password_input = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full mb-4').props('outlined')
            nombre_input = ui.input('Nombre').classes('w-full mb-3').props('outlined') 
            apellido_input = ui.input('Apellido').classes('w-full mb-3').props('outlined') 
            direccion_input = ui.input('Dirección').classes('w-full mb-4').props('outlined') 
            ui.button('Registrarse', on_click=lambda: registrar(email_input, password_input, nombre_input, apellido_input, direccion_input)).classes('w-full bg-green-600 text-white').props('push')


@ui.page('/products')
def products_page():
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} .sticky-top { position: sticky; top: 0; z-index: 100; } </style>""")
    initCombos()
    global productsContainer, cartContainer, searchField
    with ui.column().classes('min-h-screen flex flex-col'):
        with ui.row().classes('w-full flex-grow no-wrap'):
            with ui.column().classes('flex-grow p-4 overflow-hidden'):
                with ui.column().classes('sticky-top items-center').style('max-width: 900px; margin: 0 auto;'):
                    
                    # Logo a la izquierda y botones a la derecha
                    with ui.row().classes('w-full justify-between items-start q-gutter-md mb-4'):
                        # Recuadro con logo
                        with ui.card().style('padding: 10px; border: 2px solid #ccc; border-radius: 12px; background-color: white; width: 250px; min-height: 120px; display: flex; align-items: center; justify-content: center;'):
                            ui.link('Perfumería Triple C', '/').classes('font-bold text-center') \
                                .style('color: #333; font-size: 32px; text-decoration: none;') 
                        # Botones a la derecha
                        with ui.row().classes('q-gutter-md'):
                            ui.button('Mi Perfil', on_click=lambda: ui.navigate.to('/profile')).props('icon=person').classes('bg-blue-700 text-white rounded-md shadow-md hover:bg-blue-800 transition duration-300')
                            ui.button('Cerrar Sesión', on_click=logout).props('icon=logout').classes('bg-red-700 text-white rounded-md shadow-md hover:bg-red-800 transition duration-300')


                    with ui.row().classes('w-full justify-center items-center q-gutter-md mb-4'):
                        searchField = ui.input('Buscar productos...').classes('flex-grow').style('max-width: 300px;')
                        ui.button('Buscar', on_click=lambda: onSearchButtonClick(searchField)).classes('bg-blue-500 text-white')
                        ui.button('Restablecer búsqueda', on_click=onResetButtonClick).classes('bg-gray-500 text-white')


                    with ui.row().classes('q-gutter-md justify-center flex-wrap'):
                        ui.label('Filtros:').style('font-size: 24px; font-weight: bold; color: black;')
                        ui.button('Marca', on_click=toggleMarca ).classes('bg-blue-600 text-white')
                        ui.button('Aroma', on_click=toggleAroma ).classes('bg-blue-600 text-white')
                        ui.button('Duracion', on_click=toggleDuracion ).classes('bg-blue-600 text-white')
                        ui.button('Mayor Precio $', on_click=lambda: loadProducts(productsContainer, 'desc')).classes('bg-blue-600 text-white')
                        ui.button('Menor Precio $', on_click=lambda: loadProducts(productsContainer, 'asc')).classes('bg-blue-600 text-white')


                productsContainer = ui.row().classes('w-full flex-wrap justify-center gap-6 p-5 overflow-y-auto')
                loadProducts(productsContainer)
            
            with ui.column().style('width: 400px; padding: 30px; background-color: #f9f9f9; box-shadow: -2px 0px 10px rgba(0, 0, 0, 0.1); flex-shrink: 0;').classes('h-full overflow-y-auto'):
                ui.label('Carrito de compras').style('font-size: 24px; font-weight: bold; margin-bottom: 10px; text-align: center; width: 100%;')
                cartContainer = ui.column().classes('w-full')
                updateCart()
                with ui.row().classes('w-full justify-center'):
                    ui.button('Finalizar Compra', on_click=lambda: ui.notify('El carrito está vacío', type='warning') if not cart else ui.run_javascript('window.location.replace("/checkout")')
                        ).classes('bg-purple-600 text-white rounded-md shadow-md hover:bg-purple-700 transition duration-300').props('push')
                    
        with ui.row().classes('w-full flex-grow-0').style('background-color: #f1f1f1; padding: 20px; border: 1px solid black;'):
            ui.label('Compra 100% Segura. Perfumería Triple C garantiza la seguridad transaccional de sus clientes.').style('flex-grow: 1; text-align: left;')
            ui.label('CUIT: 01-34567890-1 - Calle 1234, CABA.').style('flex-grow: 1; text-align: right;')


        with ui.row().classes('w-full mt-auto flex-grow-0').style('background-color: #f1f1f1; padding: 20px; border: 1px solid black;'):
            ui.label('© 2023 Triple C. Todos los derechos reservados.').style('flex-grow: 1; text-align: left;')
            ui.link('Política de Privacidad', '/privacy').style('margin-right: 20px;')
            ui.link('Términos de Servicio', '/terms').style('margin-right: 20px;')
            ui.link('Contactos', '/contacts').style('margin-right: 5px;')


@ui.page('/promotions')
def promociones_page():
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} </style>""")
    with ui.column().classes('absolute-center items-center'):
        ui.link('Promociones', target='/').style('font-size: 32px; font-weight: bold; margin-bottom: 20px; color: white; text-decoration: none;')
        with ui.card().classes('w-96 p-4 shadow-lg'):
            ui.label('Promocion Apertura: Desde 10% hasta 40% de descuento en ciertos productos. 🎉').classes('w-full mb-3')
            ui.label('Promocion Bancaria: Tarjetas de credito VISA tienen un 5% de descuento adicional. 😁').classes('w-full mb-3')


@ui.page('/profile')
async def profile_page(): 
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} </style>""")
    with ui.column().classes('absolute-center items-center p-4'):
        ui.link('Mi Perfil', target='/').style('font-size: 28px; font-weight: bold; margin-bottom: 20px; color: white; text-decoration: none;')

        user_response = supabase.auth.get_user() 
        user = None
        if user_response and user_response.user:
            user = user_response.user
        else:
            with ui.card().classes('w-96 p-4 shadow-lg'):
                ui.label("No hay usuario logueado. Por favor, inicia sesión para ver tu perfil.").style('color: red; font-weight: bold;')
                ui.button('Ir a Iniciar Sesión', on_click=lambda: ui.navigate.to('/login')).classes('mt-4 bg-blue-600 text-white')
            return 

        try:
      
            data_response = supabase.table('users').select('id, puntos, email, nombre, apellido, direccion').eq('id', user.id).limit(1).execute() 
            user_data = None

            if data_response.data and len(data_response.data) > 0:
                user_data = data_response.data[0]
            else:
                
                print(f"No user found by ID {user.id}. Attempting to fetch by email {user.email}...")
                email_fallback_response = supabase.table('users').select('id, puntos, email, nombre, apellido, direccion').eq('email', user.email).limit(1).execute()
                if email_fallback_response.data and len(email_fallback_response.data) > 0:
                    user_data = email_fallback_response.data[0]

                    if user_data['id'] != user.id:
                        print(f"Found user by email but ID mismatch: DB ID={user_data['id']}, Auth ID={user.id}. Updating DB ID...")
                        try:
                            supabase.table('users').update({'id': user.id}).eq('email', user.email).execute()
                            user_data['id'] = user.id 
                        except Exception as update_id_e:
                            print(f"Warning: Could not update user ID for email {user.email}: {update_id_e}")
                            ui.notify(f"Advertencia: Error al sincronizar ID de perfil. Algunos datos pueden no ser exactos.", type='warning')
                else:
                    
                    print(f"No user profile found for email {user.email} in 'users' table.")
                    ui.label("No se encontraron datos adicionales para este usuario. Tu perfil puede estar incompleto o no haber sido creado aún.").style('color: orange;')
         
                    return 


            if user_data:
                with ui.card().classes('w[700px] p-4 shadow-lg'):
                    ui.label(f"Correo electrónico: {user.email}").style('font-size: 16px;')
                    ui.label(f"Nombre: {user_data.get('nombre', 'N/A')}").style('font-size: 16px;')
                    ui.label(f"Apellido: {user_data.get('apellido', 'N/A')}").style('font-size: 16px;')
                    ui.label(f"Dirección: {user_data.get('direccion', 'N/A')}").style('font-size: 16px;')
                    ui.label(f"Puntos acumulados: {user_data['puntos']}").style('font-size: 16px;')
                    ui.button(f"Cambiar Email / Contraseña", on_click=lambda: ui.navigate.to('/credenciales_imp')).classes('w-full bg-green-700 text-white mt-4').props('push')
                    ui.button(f"Cambiar Nombre / Apellido / Direccion", on_click=lambda: ui.navigate.to('/credenciales_basic')).classes('w-full bg-green-700 text-white mt-4').props('push')
            else:
                ui.label("No se encontraron datos adicionales para este usuario. Asegúrate de que tu perfil esté completo.").style('color: orange;')

        except Exception as e:
            ui.label(f"Error al cargar datos de usuario: {e}").style('color: red;')
            print(f"Error fetching user additional data: {e}")
            traceback.print_exc()


@ui.page('/credenciales_imp') 
async def credenciales_page():
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} </style>""")
    with ui.column().classes('absolute-center items-center'):
        ui.link('Cambiar Credenciales', target='/profile').style('font-size: 28px; font-weight: bold; margin-bottom: 20px; color: white; text-decoration: none;')

        user_response = supabase.auth.get_user()
        if not user_response or not user_response.user:
            with ui.card().classes('w-96 p-4 shadow-lg'):
                ui.label("No hay usuario logueado.").style('color: red; font-weight: bold;')
            return

        email_actual = user_response.user.email
        user_id = user_response.user.id


        with ui.card().classes('w-96 p-4 shadow-lg'):
            email_input = ui.input('Correo electrónico', value=email_actual).props('type=email').classes('w-full mb-3').props('outlined')
            password_input = ui.input('Nueva contraseña (Opcional)', password=True, password_toggle_button=True).classes('w-full mb-4').props('outlined')

            async def actualizar_datos():
                nuevos_datos = {}

                email_nuevo = email_input.value.strip()
                if email_nuevo != email_actual:
                    if not validate_email(email_nuevo):
                        ui.notify("Correo no válido", type="warning")
                        return
                    try:
                        await supabase.auth.update_user({'email': email_nuevo})
                        nuevos_datos["email"] = email_nuevo
                    except Exception as e:
                        ui.notify(f"Error al actualizar el correo: {e}", type="negative")
                        return

                if password_input.value:
                    if len(password_input.value) < 6:
                        ui.notify("La contraseña debe tener al menos 6 caracteres", type="warning")
                        return
                    try:
                        update_response = await supabase.auth.update_user({'password': password_input.value})

                        if hasattr(update_response, "user") and update_response.user:
                            ui.notify("Contraseña actualizada correctamente", type="positive")
                        else:
                            ui.notify("La contraseña no pudo ser actualizada. Intenta nuevamente.", type="warning")
                    except Exception as e:
                        error_message = str(e)
                        if "New password should be different" in error_message:
                            ui.notify("La nueva contraseña debe ser diferente a la actual.", type="warning")
                        else:
                            ui.notify("La contraseña se ha actualizado.", type="positive")
                            ui.navigate.to("/profile")
                        return

                if nuevos_datos:
                    try:
                        supabase.table("users").update(nuevos_datos).eq("id", user_id).execute()
                        ui.notify("Datos actualizados correctamente", type="positive")
                    except Exception as e:
                        ui.notify(f"Error al actualizar en la base de datos: {e}", type="negative")
                        return
                else:
                    ui.notify("No se realizaron cambios", type="info")

                ui.navigate.to("/profile")
            ui.button('Volver Atras', on_click=lambda: ui.navigate.to('/profile')).classes('w-full bg-green-600 text-white').props('push')
            ui.button('Finalizar Cambios', on_click=actualizar_datos).classes('w-full bg-green-600 text-white').props('push')


@ui.page('/credenciales_basic')
async def credenciales_page():
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} </style>""")
    with ui.column().classes('absolute-center items-center'):
        ui.link('Cambiar Credenciales', target='/profile').style('font-size: 28px; font-weight: bold; margin-bottom: 20px; color: white; text-decoration: none;')

        user_response = supabase.auth.get_user()
        if not user_response or not user_response.user:
            with ui.card().classes('w-96 p-4 shadow-lg'):
                ui.label("No hay usuario logueado.").style('color: red; font-weight: bold;')
            return

        user_id = user_response.user.id

        user_data_response = supabase.table('users').select("*").eq("id", user_id).single().execute()
        user_data = user_data_response.data if user_data_response.data else {}

        with ui.card().classes('w-96 p-4 shadow-lg'):
            nombre_input = ui.input('Nombre', value=user_data.get("nombre", "")).classes('w-full mb-3').props('outlined') 
            apellido_input = ui.input('Apellido', value=user_data.get("apellido", "")).classes('w-full mb-3').props('outlined') 
            direccion_input = ui.input('Dirección', value=user_data.get("direccion", "")).classes('w-full mb-4').props('outlined') 

            async def actualizar_datos():
                nuevos_datos = {}

                if nombre_input.value != user_data.get("nombre"):
                    nuevos_datos["nombre"] = nombre_input.value
                if apellido_input.value != user_data.get("apellido"):
                    nuevos_datos["apellido"] = apellido_input.value

                if direccion_input.value != user_data.get("direccion"):
                    if not validate_direccion(direccion_input.value):
                        ui.notify("Dirección no válida", type="warning")
                        return
                    nuevos_datos["direccion"] = direccion_input.value


                if nuevos_datos:
                    try:
                        supabase.table("users").update(nuevos_datos).eq("id", user_id).execute()
                        ui.notify("Datos actualizados correctamente", type="positive")
                    except Exception as e:
                        ui.notify(f"Error al actualizar en la base de datos: {e}", type="negative")
                        return
                else:
                    ui.notify("No se realizaron cambios", type="info")

                ui.navigate.to("/profile")

            ui.button('Volver Atras', on_click=lambda: ui.navigate.to('/profile')).classes('w-full bg-green-600 text-white').props('push')
            ui.button('Finalizar Cambios', on_click=actualizar_datos).classes('w-full bg-green-600 text-white').props('push')


@ui.page('/checkout', response_timeout=25.0)
async def checkout_page():
    ui.add_head_html("""
    <style>
        body {
            background-image: url('/img/fondo.png');
            background-size: cover;
            background-attachment: fixed;
            font-family: 'Inter', sans-serif;
        }
        .checkout-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        .summary-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border: 1px solid #e5e7eb;
        }
        .payment-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border: 1px solid #e5e7eb;
        }
        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #111827;
            border-bottom: 2px solid #f3f4f6;
            padding-bottom: 0.75rem;
            margin-bottom: 1.5rem;
        }
        .cart-item {
            transition: all 0.2s ease;
            border-bottom: 1px solid #f5f5f5;
        }
        .cart-item:hover {
            background-color: #f9fafb;
        }
        .btn-primary {
            background: #4f46e5;
            color: white;
            transition: all 0.2s ease;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 500;
        }
        .btn-primary:hover {
            background: #4338ca;
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .points-badge {
            background: #fef3c7;
            color: #92400e;
            font-weight: 500;
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            font-size: 0.75rem;
        }
        .input-field {
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            padding: 0.75rem;
            transition: all 0.2s ease;
        }
        .input-field:focus {
            border-color: #4f46e5;
            box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
        }
        .total-row {
            border-top: 2px solid #f3f4f6;
            padding-top: 1rem;
        }
    </style>
    """)
    
    global cartContainer, last_purchase, cart 


    with ui.column().classes('absolute-center items-center p-4'):
        ui.link('Finalizar Compra', target='/products').style('font-size: 28px; font-weight: bold; color: white; text-decoration: none;')

        # Sección Resumen del Carrito
        with ui.card().classes('w-full max-w-2xl p-4 shadow-lg'):
            ui.label('Resumen del Carrito:').style('font-size: 20px; font-weight: bold; margin-bottom: 15px; text-align: center;')
            
            cartContainer = ui.column().classes('w-full border p-2 mb-4 rounded overflow-y-auto').style('max-height: 250px;')
            updateCart() 
            
            # Sección Información de Envío
            with ui.expansion('Información de Envío', icon='local_shipping').classes('w-full mt-4'):
                with ui.column().classes('w-full gap-4'):

                    # Tipo de envío
                    shipping_method = ui.select(
                        options=['Retiro en local', 'Envío estándar (3-5 días)', 'Envío express (24-48 hrs)'],
                        label='Método de envío',
                        value='Envío estándar (3-5 días)',
                        validation={'Selecciona un método de envío': lambda val: bool(val)}
                    ).classes('w-full')
                    
                    # Grupo de campos de envío (solo visibles cuando no es retiro en local)
                    with ui.column().bind_visibility_from(shipping_method, 'value', lambda val: val != 'Retiro en local'):
                        shipping_address = ui.textarea(
                            label='Dirección completa',
                            validation={
                                'Dirección requerida': lambda val: bool(val.strip()),
                                'Dirección muy corta': lambda val: len(val.strip()) >= 10
                            }
                        ).classes('w-full')
                        
                        with ui.row().classes('w-full gap-4'):
                            postal_code = ui.input(
                                label='Código Postal',
                                validation={
                                    'Código postal requerido': lambda val: bool(val),
                                    'Debe tener 4 dígitos': lambda val: len(val) == 4 and val.isdigit()
                                }
                            ).classes('flex-grow').props('mask=####')
                            
                            city = ui.input(
                                label='Localidad',
                                validation={'Localidad requerida': lambda val: bool(val.strip())}
                            ).classes('flex-grow')
                        
                        province = ui.select(
                            options=['Buenos Aires', 'CABA', 'Catamarca', 'Chaco', 'Chubut', 
                                    'Córdoba', 'Corrientes', 'Entre Ríos', 'Formosa', 'Jujuy',
                                    'La Pampa', 'La Rioja', 'Mendoza', 'Misiones', 'Neuquén',
                                    'Río Negro', 'Salta', 'San Juan', 'San Luis', 'Santa Cruz',
                                    'Santa Fe', 'Santiago del Estero', 'Tierra del Fuego', 'Tucumán'],
                            label='Provincia',
                            validation={'Selecciona una provincia': lambda val: bool(val)}
                        ).classes('w-full')

            descuento_por_puntos = {'aplicado': False, 'monto': 0, 'puntos_usados': 0}


            puntos_label = ui.label('').style('text-align: center; font-size: 14px; color: green; font-weight: bold;')
            
            ui.separator().classes('my-4')
            ui.label('Detalles de Pago').style('font-size: 20px; font-weight: bold; margin-bottom: 15px; text-align: center; width: 100%;')


            name_input = ui.input('Nombre en la tarjeta').classes('w-full mb-3').props('outlined')
            card_input = ui.input('Número de tarjeta').classes('w-full mb-3').props('outlined mask="#### #### #### ####" hint="XXXX XXXX XXXX XXXX"')
            with ui.row().classes('w-full justify-between'):
                exp_input = ui.input('Fecha de vencimiento').classes('w-2/5').props('outlined mask="##/##" placeholder="MM/YY"')
                cvv_input = ui.input('CVV').classes('w-2/5').props('outlined mask="####" hint="123 o 1234"')

            amount_to_redeem_cart = ui.number('Puntos a canjear', value=0, format='%.0f', min=0).classes('w-full mb-4')

            ui.button('Canjear Puntos', on_click=lambda: redeemPoints(None, amount_to_redeem_cart.value)).classes('bg-green-600 text-white w-full mb-4')


            def luhn_check(card_number: str) -> bool:
                total = 0
                reverse_digits = card_number[::-1]
                for i, digit in enumerate(reverse_digits):
                    n = int(digit)
                    if i % 2 == 1:
                        n *= 2
                        if n > 9:
                            n -= 9
                    total += n
                return total % 10 == 0


            def detect_card_type(card_number: str) -> str:
                if re.match(r"^4[0-9]{12}(?:[0-9]{3})?$", card_number):
                    return "VISA"
                elif re.match(r"^5[1-5][0-9]{14}$", card_number):
                    return "MasterCard"
                elif re.match(r"^3[47][0-9]{13}$", card_number):
                    return "American Express"
                elif re.match(r"^6(?:011|5[0-9]{2})[0-9]{12}$", card_number):
                    return "Discover"
                else:
                    return "Tipo de tarjeta desconocido"


            def validate_expiration_date(expiration: str) -> bool:
                try:
                    exp_date = datetime.strptime(expiration, "%m/%y")
                    now = datetime.now()
                    return exp_date.year > now.year or (exp_date.year == now.year and exp_date.month >= now.month)
                except ValueError:
                    return False


            def validate_cvv(cvv: str, card_type: str) -> bool:
                if card_type == "American Express":
                    return len(cvv) == 4 and cvv.isdigit()
                return len(cvv) == 3 and cvv.isdigit()


            async def aplicar_descuento_con_puntos():
                user = supabase.auth.get_user().user
                if not user:
                    ui.notify("Inicia sesión para canjear puntos", type="warning")
                    return

                user_id = user.id
                user_data_response = supabase.table('users').select('puntos').eq('id', user_id).single().execute()

                if not user_data_response.data:
                    ui.notify("No se pudo obtener la información del usuario.", type="negative")
                    return

                current_points = user_data_response.data['puntos']

                PUNTOS_POR_DESCUENTO = 100
                MONTO_DESCUENTO_POR_PUNTOS = 10

                if current_points < PUNTOS_POR_DESCUENTO:
                    ui.notify(f"Necesitás al menos {PUNTOS_POR_DESCUENTO} puntos para canjear.", type="warning")
                    return

                redeemable_blocks = current_points // PUNTOS_POR_DESCUENTO
                points_to_deduct = redeemable_blocks * PUNTOS_POR_DESCUENTO
                
                descuento = redeemable_blocks * MONTO_DESCUENTO_POR_PUNTOS

                descuento_por_puntos['aplicado'] = True
                descuento_por_puntos['monto'] = descuento
                descuento_por_puntos['puntos_usados'] = points_to_deduct

                new_points = current_points - points_to_deduct
                update_response = supabase.table('users').update({'puntos': new_points}).eq('id', user_id).execute()


                if update_response.data:
                    ui.notify(f"Has canjeado {points_to_deduct} puntos por un descuento de ${descuento:.2f}. Puntos restantes: {new_points}.", type="positive")
                    puntos_label.text = f"Descuento aplicado: ${descuento:.2f} usando {points_to_deduct} puntos."
                else:
                    ui.notify("Error al aplicar el canje de puntos en la base de datos.", type="negative")


            async def redeemPoints(user_email_param: None, points_to_redeem: int):
                user_session_for_redeem = supabase.auth.get_user()
                if not user_session_for_redeem or not user_session_for_redeem.user:
                    ui.notify("Inicia sesión para canjear puntos.", type="warning")
                    return

                user_id_for_redeem = user_session_for_redeem.user.id

                user_data_response = supabase.table('users').select('puntos').eq('id', user_id_for_redeem).single().execute()
                if not user_data_response.data:
                    ui.notify("No se pudo obtener tu información de puntos.", type="negative")
                    return

                current_points = user_data_response.data['puntos']
                points_to_redeem = int(points_to_redeem)

                if points_to_redeem <= 0:
                    ui.notify("Ingresa una cantidad de puntos válida para canjear.", type="warning")
                    return


                if points_to_redeem > current_points:
                    ui.notify(f"No tienes suficientes puntos. Puntos actuales: {current_points}.", type="warning")
                    return

                PUNTOS_POR_DESCUENTO = 100
                MONTO_DESCUENTO_POR_PUNTOS = 10

                if points_to_redeem % PUNTOS_POR_DESCUENTO != 0:
                    ui.notify(f"Solo puedes canjear puntos en múltiplos de {PUNTOS_POR_DESCUENTO}.", type="warning")
                    return

                calculated_discount = (points_to_redeem / PUNTOS_POR_DESCUENTO) * MONTO_DESCUENTO_POR_PUNTOS
                total_actual = sum(item['product'].getPriceForCapacity(item['capacity']) * item['quantity'] for item in cart)

                if calculated_discount > total_actual:
                    ui.notify(f"No podés canjear tantos puntos porque el descuento (${calculated_discount:.2f}) supera el total (${total_actual:.2f}).", type="warning")
                    return

                # Se guardan los valores para usar en la confirmación
                descuento_por_puntos['aplicado'] = True
                descuento_por_puntos['monto'] = calculated_discount
                descuento_por_puntos['puntos_usados'] = points_to_redeem

                puntos_label.text = f"Descuento aplicado: ${calculated_discount:.2f} usando {points_to_redeem} puntos."
                ui.notify("Descuento aplicado. Se descontarán los puntos al confirmar la compra.", type="info")


            async def update_product_stock(product_id: str, capacity: int, quantity: int):
                """Updates the stock of a product in the Supabase 'perfumes' table."""
                try:
                    product_data_response = supabase.table('perfumes').select(f'stock_{capacity}ml').eq('id', product_id).limit(1).execute()

                    if product_data_response.data and len(product_data_response.data) > 0:
                        current_stock_key = f'stock_{capacity}ml'
                        current_stock = product_data_response.data[0].get(current_stock_key, 0)

                        new_stock = current_stock - quantity

                        if new_stock < 0:
                            ui.notify(f'¡Advertencia! Stock insuficiente para el producto ID {product_id} ({capacity}ml). Stock actual: {current_stock}, Cantidad solicitada: {quantity}', type='warning')
                            return False

                        update_data = {current_stock_key: new_stock}

                        update_response = supabase.table('perfumes').update(update_data).eq('id', product_id).execute()

                        if update_response.data:
                            print(f"Stock actualizado para producto {product_id} ({capacity}ml): {new_stock}")
                            return True
                        else:
                            ui.notify(f'Error al actualizar stock para producto {product_id} ({capacity}ml): {update_response.get("message", "Error desconocido")}', type='negative')
                            print(f"Supabase update error: {update_response}")
                            return False
                    else:
                        ui.notify(f'Producto ID {product_id} no encontrado para actualizar stock.', type='warning')
                        return False

                except Exception as e:
                    ui.notify(f'Error inesperado al actualizar stock: {e}', type='negative')
                    print(f"Error in update_product_stock: {e}")
                    traceback.print_exc()
                    return False


            async def confirm_purchase():
                global last_purchase, cart

                user_session = supabase.auth.get_user()
                if not user_session or not user_session.user:
                    ui.notify("Debes iniciar sesión para finalizar la compra.", type="warning")
                    ui.navigate.to('/login')
                    return
                user_id = user_session.user.id
                user_email = user_session.user.email 


                if not cart:
                    ui.notify("El carrito está vacío. Agrega productos para confirmar la compra.", type="warning")
                    return


                arbol_carrito = BinaryTree()
                for item in cart:
                    arbol_carrito.agregar(item)
                productos_ordenados = arbol_carrito.recorrido_in_order() 


                name = name_input.value.strip()
                card = card_input.value.strip().replace(" ", "")
                exp = exp_input.value.strip()
                cvv = cvv_input.value.strip()


                if not all([name, card, exp, cvv]):
                    ui.notify('Todos los campos deben estar completos.', type='negative')
                    return


                if not name.replace(" ", "").isalpha():
                    ui.notify('El nombre en la tarjeta solo puede contener letras.', type='warning')
                    return


                if not card.isdigit():
                    ui.notify('El número de tarjeta debe contener solo dígitos.', type='warning')
                    return


                card_type = detect_card_type(card)
                if card_type == "Tipo de tarjeta desconocido":
                    ui.notify("No se pudo efectuar la compra. Aceptamos VISA, MasterCard, American Express y Discover.", type="negative")
                    return


                if card_type == "American Express" and len(card) != 15:
                    ui.notify('Las tarjetas American Express deben tener 15 dígitos.', type='warning')
                    return
                elif card_type != "American Express" and len(card) != 16:
                    ui.notify(f'Las tarjetas {card_type} deben tener 16 dígitos.', type='warning')
                    return


                if not luhn_check(card):
                    ui.notify('El número de tarjeta no es válido (Fallo en Luhn Check).', type='negative')
                    return


                if not validate_expiration_date(exp):
                    ui.notify('La tarjeta ya está vencida o la fecha es inválida.', type='negative')
                    return


                if not validate_cvv(cvv, card_type):
                    ui.notify('El código de seguridad (CVV) no es válido para este tipo de tarjeta.', type='negative')
                    return


                # VALIDACIÓN DE DATOS DE ENVÍO
                if shipping_method.value != 'Retiro en local':
                    direccion_ingresada = shipping_address.value.strip()

                    if not direccion_ingresada:
                        ui.notify("Debes ingresar una dirección válida de envío.", type="warning")
                        return
                    if not postal_code.value or len(postal_code.value.strip()) != 4:
                        ui.notify("El código postal debe tener 4 dígitos.", type="warning")
                        return
                    if not city.value or not city.value.strip():
                        ui.notify("Debes ingresar una localidad.", type="warning")
                        return
                    if not province.value:
                        ui.notify("Debes seleccionar una provincia.", type="warning")
                        return

                    # VALIDACIÓN de coincidencia con la dirección en la base de datos
                    try:
                        user_data_resp = supabase.table('users').select('direccion').eq('id', user_id).single().execute()
                        direccion_registrada = user_data_resp.data.get('direccion') if user_data_resp.data else None

                        if direccion_ingresada != direccion_registrada:
                            ui.notify("La dirección ingresada no coincide con la registrada en tu cuenta.", type="negative")
                            return
                    except Exception as e:
                        ui.notify("Error al verificar la dirección registrada.", type="negative")
                        print("Error obteniendo dirección del usuario:", e)
                        return



                ui.notify(f'{card_type} detectada. Procesando compra...', type='info')


                total = 0
                resumen_items = []
                for item in productos_ordenados: 
                    product = item['product']
                    capacity = item['capacity']
                    quantity = item['quantity']
                    price = product.getPriceForCapacity(capacity)


                    total += price * quantity
                    resumen_items.append({
                        'product_id': product.id,
                        'name': product.getName(),
                        'capacity': capacity,
                        'quantity': quantity,
                        'price': price,
                        'subtotal': price * quantity
                    })


                if descuento_por_puntos['aplicado']:
                    total -= descuento_por_puntos['monto']
                    total = max(total, 0)


                shipping_cost = 0
                if shipping_method.value != 'Retiro en local':
                    shipping_cost = 10.00 
                    total += shipping_cost


                for item in productos_ordenados:
                    product = item['product']
                    capacity = item['capacity']
                    quantity = item['quantity']
                    stock_updated = await update_product_stock(product.id, capacity, quantity)
                    if not stock_updated:
                        ui.notify(f'No se pudo actualizar el stock para {product.getName()} ({capacity}ml). Compra cancelada.', type='negative')
                        return


                try:
                    points_to_add = int(total / 10)


                    user_profile_response = supabase.table('users').select('id, puntos, email, nombre, apellido, direccion').eq('id', user_id).limit(1).execute()


                    user_profile_data = None
                    if user_profile_response.data and len(user_profile_response.data) > 0:
                        user_profile_data = user_profile_response.data[0]
                    else:
                        print(f"User profile not found by ID {user_id}. Trying by email {user_email}...")
                        email_fallback_response = supabase.table('users').select('id, puntos, email, nombre, apellido, direccion').eq('email', user_email).limit(1).execute()
                        if email_fallback_response.data and len(email_fallback_response.data) > 0:
                            user_profile_data = email_fallback_response.data[0]
                            if user_profile_data['id'] != user_id:
                                print(f"Found profile by email but ID mismatch. Updating ID...")
                                try:
                                    supabase.table('users').update({'id': user_id}).eq('email', user_email).execute()
                                    user_profile_data['id'] = user_id 
                                except Exception as update_id_e:
                                    print(f"Warning: Failed to update user ID: {update_id_e}")


                    if user_profile_data:
                        current_points = user_profile_data.get('puntos', 0)
                        new_total_points = current_points + points_to_add


                        # Descontar puntos canjeados si se aplicó descuento
                        if descuento_por_puntos['aplicado'] and descuento_por_puntos['puntos_usados'] > 0:
                            new_total_points -= descuento_por_puntos['puntos_usados']
                            new_total_points = max(new_total_points, 0)
                            ui.notify(f'Se descontaron {descuento_por_puntos["puntos_usados"]} puntos. Puntos restantes: {new_total_points}', type='positive')


                        update_points_response = supabase.table('users').update({'puntos': new_total_points}).eq('id', user_id).execute()


                        if update_points_response.data:
                            ui.notify(f'¡Has ganado {points_to_add} puntos! Total: {new_total_points} puntos.', type='positive')
                        else:
                            ui.notify(f'Error al actualizar puntos.', type='warning')
                            print(f"Supabase update error: {update_points_response}")
                    else:
                        new_total_points = points_to_add
                        insert_user_profile_response = supabase.table('users').insert({
                            'id': user_id,
                            'email': user_email,
                            'puntos': new_total_points,
                            'nombre': None,
                            'apellido': None,
                            'direccion': None,
                        }).execute()


                        if insert_user_profile_response.data:
                            ui.notify(f'¡Bienvenido! Has ganado {points_to_add} puntos. Total: {new_total_points} puntos.', type='positive')
                        else:
                            ui.notify(f'Error al crear perfil de usuario.', type='warning')
                            print(f"Insert error: {insert_user_profile_response}")


                except Exception as e:
                    ui.notify(f'Error inesperado al gestionar puntos: {e}', type='negative')
                    print(f"Error: {e}")
                    traceback.print_exc()


                try:
                    purchase_data = {
                        'user_email': user_email,
                        'total_amount': total,
                        'purchase_date': datetime.now().isoformat(),
                        'points_earned': points_to_add,
                        'items': [{'product_id': item['product_id'], 'capacity': item['capacity'], 'quantity': item['quantity'], 'price_at_purchase': item['price']} for item in resumen_items]
                    }
                    insert_purchase_response = supabase.table('purchase_history').insert(purchase_data).execute()


                    if not insert_purchase_response.data:
                        ui.notify("Error al registrar la compra en la base de datos.", type='negative')
                        print(f"Insert error: {insert_purchase_response}")
                        return


                except Exception as e:
                    ui.notify(f"Error al registrar la compra: {e}", type='negative')
                    traceback.print_exc()
                    return

                last_purchase = {
                    'items': resumen_items,
                    'total': total, 
                    'name': name,
                    'card_type': card_type,
                    'discount_applied': descuento_por_puntos['aplicado'], 
                    'discount_amount': descuento_por_puntos['monto'],     
                    'points_used_for_discount': descuento_por_puntos['puntos_usados'],
                    'shipping_cost': shipping_cost
                }

                cart.clear()
                updateCart()
                descuento_por_puntos['aplicado'] = False 
                descuento_por_puntos['monto'] = 0
                descuento_por_puntos['puntos_usados'] = 0

                ui.notify('¡Compra finalizada con éxito!', duration=3, type='positive')
                ui.navigate.to('/purchase-detail')

            ui.button('Confirmar Compra', on_click=confirm_purchase).classes('w-full bg-green-700 text-white mt-4').props('push')
            ui.button('Agregar Perfumes', on_click=lambda: ui.navigate.to('/products')).classes('w-full bg-blue-500 text-white mt-2').props('push')
            ui.button('Cancelar Compra', on_click=lambda: (cart.clear(), updateCart(), ui.notify("Compra cancelada", type="info"), ui.navigate.to('/products'))).classes('w-full bg-red-600 text-white mt-2').props('push')


def pdf_factura(html: str) -> bytes:
    pdf_buffer = BytesIO()
    HTML(string=html).write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()


def enviar_factura(destinatario, asunto, mensaje_html):
    msg = MIMEMultipart()
    msg['From'] = smtp_email
    msg['To'] = destinatario
    msg['Subject'] = asunto


    body_text = "Adjuntamos tu factura en PDF. Gracias por tu compra en Triple C."
    msg.attach(MIMEText(body_text, 'plain'))


    pdf_bytes = pdf_factura(mensaje_html)
    pdf_attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
    pdf_attachment.add_header('Content-Disposition', 'attachment', filename='Factura_TripleC.pdf')
    msg.attach(pdf_attachment)


    partes = msg.get_payload()
    if isinstance(partes, list):
        print("Adjuntos totales (incluyendo texto):", len(partes))


    # Enviar el correo
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_email, smtp_pass)
        server.send_message(msg)


    print(f"Factura PDF enviada a {destinatario}")


def generar_factura_html(last_purchase):
    items_html = "".join([
        f"<li>{item['name']} ({item['capacity']} ml) x {item['quantity']} - ${item['subtotal']:.2f}</li>"
        for item in last_purchase['items']
    ])


    shipping_cost = last_purchase.get('shipping_cost', 0)
    total_sin_descuento = sum(item['subtotal'] for item in last_purchase['items']) + shipping_cost


    descuento_html = ""
    total_final = total_sin_descuento


    # Descuento por puntos
    if last_purchase.get('discount_applied'):
        descuento_html += f"""
            <p style='color: green;'>Descuento aplicado: -${last_purchase['discount_amount']:.2f} 
            (usando {last_purchase['points_used_for_discount']} puntos)</p>
        """
        total_final -= last_purchase['discount_amount']


    # Descuento adicional por tarjeta VISA
    if last_purchase.get('card_type') == "VISA":
        descuento_visa = total_final * 0.05
        total_final *= 0.95
        descuento_html += f"""
            <p style='color: green;'>Descuento por pagar con VISA: -${descuento_visa:.2f}</p>
        """


    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #2c3e50;">Factura de Perfumería Triple C</h2>
            <p>Gracias por tu compra. Aquí está el resumen:</p>
            <ul>{items_html}</ul>
            <p>Envío: ${shipping_cost:.2f}</p>
            <p>Total antes de descuentos: ${total_sin_descuento:.2f}</p>
            {descuento_html}
            <p><strong>Total pagado: ${total_final:.2f}</strong></p>
            <p>Método de pago: {last_purchase['card_type']}</p>
            <p>Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <p style="font-size: 12px; color: #999;">Triple C - Gracias por tu compra</p>
        </body>
    </html>
    """
    return html


@ui.page('/purchase-detail')
def purchase_detail():
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} </style>""")
    global last_purchase


    if not last_purchase:
        ui.label("No hay detalles de compra disponibles.").style('color: red;')
        ui.button('Volver a Productos', on_click=lambda: ui.navigate.to('/products'))
        return


    # --- Enviar factura al usuario ---
    try:
        user = supabase.auth.get_user()
        if user and user.user:
            user_email = user.user.email
            factura_html = generar_factura_html(last_purchase)
            enviar_factura(
                destinatario=user_email,
                asunto="Factura de tu compra en Perfumería Triple C",
                mensaje_html=factura_html
            )
        else:
            print("No se pudo obtener el usuario logueado para enviar factura.")
    except Exception as e:
        print(f"Error al enviar factura: {e}")


    # --- Mostrar en pantalla ---
    with ui.column().classes('absolute-center items-center p-4'):
        ui.link('Detalle de Compra', target='/').style('font-size: 28px; font-weight: bold; color: white; text-decoration: none;')
        with ui.card().classes('w-96 p-4 shadow-lg'):
            ui.label('Resumen de la Compra:').style('font-size: 20px; font-weight: bold; margin-bottom: 15px; text-align: center; width: 100%;')


            for item in last_purchase['items']:
                ui.label(f"{item['name']} ({item['capacity']} ml) - Cantidad: {item['quantity']} - Subtotal: ${item['subtotal']:.2f}").classes('w-full')


            ui.separator().classes('my-2')


            subtotal_productos = sum(item['subtotal'] for item in last_purchase['items'])
            shipping_cost = last_purchase.get('shipping_cost', 0)
            descuento = last_purchase.get('discount_amount', 0) if last_purchase.get('discount_applied', False) else 0


            # Mostrar costo de productos separado del envío
            ui.label(f"Costo de Productos: ${subtotal_productos:.2f}").style('text-align: center; width: 100%; font-weight: bold;')


            if shipping_cost > 0:
                ui.label(f"Costo de Envío: ${shipping_cost:.2f}").style('text-align: center; width: 100%; font-weight: bold;')


            if descuento > 0:
                ui.label(f"Descuento aplicado: -${descuento:.2f} (usando {last_purchase['points_used_for_discount']} puntos)").style('color: green; font-weight: bold; text-align: center; width: 100%;')


            ui.separator().classes('my-2')


            total_calculado = subtotal_productos + shipping_cost - descuento


            if last_purchase['card_type'] == "VISA":
                ui.label(f"Total Pagado: ${total_calculado * 0.95:.2f}").style('font-weight: bold; font-size: 1.2em; text-align: center; width: 100%;')
                ui.label(f"Descuento del 5% por Promocion de VISA").style('font-size: 1.2em; text-align: center; width: 100%;')
            else:
               ui.label(f"Total Pagado: ${total_calculado:.2f}").style('font-weight: bold; font-size: 1.2em; text-align: center; width: 100%;') 


            ui.label(f"Pagado con: {last_purchase['card_type']}").style('text-align: center; width: 100%;')


            ui.button('Volver a Productos', on_click=lambda: ui.navigate.to('/products')).classes('w-full bg-blue-500 text-white mt-4').props('push')




@ui.page('/privacy')
def privacy_page():
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} </style>""")
    with ui.column().classes('w-full'):


        with ui.row().classes('w-full items-center justify-between p-4 border border-black bg-white'):
            ui.image('/img/logo_triplec.png').on('click', lambda: ui.navigate.to('/')).style('height: 100px; width: 200px; object-fit: contain;').classes('cursor-pointer')
            with ui.row().classes('gap-4'):
                ui.button('Registro', on_click=lambda: ui.navigate.to('/registro')).classes('bg-blue-600 border border-black text-white')
                ui.button('Login', on_click=lambda: ui.navigate.to('/login')).classes('bg-blue-600 border border-black text-white')


        with ui.row().classes('w-full items-center justify-between p-2 border border-black bg-white'):
            with ui.row().classes('gap-6'):
                ui.button('Productos', on_click=lambda: ui.navigate.to('/products')).classes('bg-blue-600 border-none text-white')
                ui.button('Promociones', on_click=lambda: ui.navigate.to('/promotions')).classes('bg-blue-600 border-none text-white')
            ui.label('¡SALE!  - Descuentos imperdibles, solo por tiempo limitado. HASTA un 40% OFF en productos seleccionados').classes('text-sm')
        
        politicaDePrivacidad = [
            "POLÍTICA DE PRIVACIDAD",
            "Última actualización: 11/06/2025",
            "",
            "En Triple C, nos comprometemos firmemente a proteger la privacidad de nuestros usuarios. Esta Política de Privacidad describe de forma clara cómo recopilamos, utilizamos, almacenamos y resguardamos la información personal proporcionada al utilizar nuestra tienda en línea, dedicada exclusivamente a la comercialización de perfumes.",
            "",
            "La información que recolectamos incluye datos personales como nombre completo, dirección de correo electrónico, dirección física, número telefónico y datos de pago, los cuales son procesados exclusivamente por plataformas de pago certificadas y seguras. También se recopila información técnica, como dirección IP, tipo de navegador, duración de la visita y comportamiento de navegación mediante cookies.",
            "",
            "La finalidad principal del tratamiento de los datos personales es permitir la correcta gestión de pedidos, ofrecer una experiencia personalizada, mantener una comunicación eficiente con nuestros clientes y cumplir con nuestras obligaciones legales. Solo compartimos esta información con terceros que prestan servicios esenciales, como operadores logísticos y plataformas de pago, siempre bajo estrictas condiciones de confidencialidad.",
            "",
            "Contamos con medidas de seguridad técnicas y organizativas para proteger la integridad y confidencialidad de los datos personales. Utilizamos protocolos de cifrado, conexiones seguras (SSL), acceso restringido y almacenamiento seguro.",
            "",
            "Los usuarios tienen pleno derecho a acceder, modificar, actualizar o solicitar la eliminación de sus datos personales en cualquier momento, así como a revocar el consentimiento previamente otorgado. Para ejercer estos derechos, puede comunicarse con nosotros escribiendo a soporteclientetriplec@gmail.com.",
            "",
            "El uso de cookies en nuestro sitio está orientado a mejorar la experiencia de navegación. El usuario puede configurar su navegador para rechazarlas, aunque algunas funcionalidades podrían verse afectadas.",
            "",
            "Nos reservamos el derecho de actualizar esta Política de Privacidad en cualquier momento. Cualquier cambio significativo será debidamente comunicado a través de nuestro sitio web."]
        
        with ui.row().classes('items-center justify-between w-full').style('height: 700px;'):
            ui.button('').props('flat').classes('w-1 h-1 opacity-0')


            with ui.card().classes('w-full border border-black').style('height: 550px;'):
                for linea in politicaDePrivacidad:
                    ui.label(linea).classes('whitespace-pre-wrap')


            ui.button('').props('flat').classes('w-1 h-1 opacity-0')


        with ui.row().style('width: 100%; background-color: #f1f1f1; padding: 20px; margin-top: 10px; border: 1px solid black;'):
            ui.label('Compra 100% Segura. Perfumería Triple C garantiza la seguridad transaccional de sus clientes.').style('flex-grow: 1; text-align: left;')
            ui.label('CUIT: 01-34567890-1 - Calle 1234, CABA.').style('flex-grow: 1; text-align: right;')


        with ui.row().style('width: 100%; background-color: #f1f1f1; padding: 20px; margin-top: 10px; border: 1px solid black;'):
            ui.label('© 2023 Triple C. Todos los derechos reservados.').style('flex-grow: 1; text-align: left;')
            ui.link('Política de Privacidad', '/privacy').style('margin-right: 20px;')
            ui.link('Términos de Servicio', '/terms').style('margin-right: 20px;')
            ui.link('Contacto', '/contacts').style('margin-right: 5px;')


@ui.page('/terms')
def terms_page():
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} </style>""")
    with ui.column().classes('w-full'):


        with ui.row().classes('w-full items-center justify-between p-4 border border-black bg-white'):
            ui.image('/img/logo_triplec.png').on('click', lambda: ui.navigate.to('/')).style('height: 100px; width: 200px; object-fit: contain;').classes('cursor-pointer')
            with ui.row().classes('gap-4'):
                ui.button('Registro', on_click=lambda: ui.navigate.to('/registro')).classes('bg-blue-600 border border-black text-white')
                ui.button('Login', on_click=lambda: ui.navigate.to('/login')).classes('bg-blue-600 border border-black text-white')


        with ui.row().classes('w-full items-center justify-between p-2 border border-black bg-white'):
            with ui.row().classes('gap-6'):
                ui.button('Productos', on_click=lambda: ui.navigate.to('/products')).classes('bg-blue-600 border-none text-white')
                ui.button('Promociones', on_click=lambda: ui.navigate.to('/promotions')).classes('bg-blue-600 border-none text-white')
            ui.label('¡SALE!  - Descuentos imperdibles, solo por tiempo limitado. HASTA un 40% OFF en productos seleccionados').classes('text-sm')
        
        terminosDeServicio = [
            "TÉRMINOS Y CONDICIONES DE SERVICIO",
            "Última actualización: 11/06/2025",
            "",
            "Bienvenido/a a Triple C, la tienda virtual especializada en la venta de perfumes. El acceso y uso de este sitio web implican la aceptación plena de los presentes Términos y Condiciones. Recomendamos su lectura atenta antes de efectuar cualquier transacción.",
            "",
            "El usuario declara que la información suministrada es verídica y actualizada, comprometiéndose a utilizar el sitio de manera lícita y responsable.",
            "",
            "Los productos exhibidos están sujetos a disponibilidad y pueden sufrir modificaciones sin previo aviso. Las imágenes y descripciones han sido elaboradas con el mayor cuidado, aunque pueden presentar leves variaciones respecto al producto real debido a diferencias de visualización en los dispositivos electrónicos.",
            "",
            "Los precios están expresados en Dólares Estadounidenses (USD$) e incluyen los impuestos aplicables según la legislación vigente. Las transacciones son procesadas a través de plataformas seguras y reconocidas. Nos reservamos el derecho de modificar los precios en cualquier momento sin necesidad de notificación previa.",
            "",
            "El servicio de entrega se realiza a través de operadores logísticos confiables. Los plazos estimados de entrega pueden variar por factores externos a nuestra empresa. Es responsabilidad del cliente garantizar la exactitud de la información proporcionada para el envío.",
            "",
            "Las solicitudes de cambio o devolución solo serán aceptadas cuando el producto recibido se encuentre dañado o no corresponda con lo adquirido. El reclamo deberá realizarse dentro de los 30 días posteriores a la recepción. Los perfumes deben conservar su empaque original, sin haber sido utilizados ni abiertos.",
            "",
            "Todo el contenido presente en el sitio, incluyendo imágenes, textos, logotipos y diseño, es propiedad exclusiva de Triple C o cuenta con las licencias correspondientes. Queda prohibida su reproducción total o parcial sin autorización expresa.",
            "",
            "La empresa no se hace responsable por daños directos o indirectos derivados del uso del sitio, por interrupciones en el servicio o por contenidos de terceros a los que se pueda acceder mediante enlaces.",
            "",
            "Nos reservamos el derecho de modificar estos Términos y Condiciones en cualquier momento. Las modificaciones serán efectivas a partir de su publicación en el sitio web.",
            "",
            "Para cualquier consulta, reclamo o solicitud de información adicional, puede comunicarse con nuestro equipo de atención al cliente escribiendo a soporteclientetriplec@gmail.com."]


        with ui.row().classes('items-center justify-between w-full').style('margin-bottom: 30px;'):
            ui.button('').props('flat').classes('w-1 h-1 opacity-0')


            with ui.card().classes('w-full border border-black').style('height: 700px;'):
                for linea in terminosDeServicio:
                    ui.label(linea).classes('whitespace-pre-wrap')


            ui.button('').props('flat').classes('w-1 h-1 opacity-0')


        with ui.row().style('width: 100%; background-color: #f1f1f1; padding: 20px; margin-top: 10px; border: 1px solid black;'):
            ui.label('Compra 100% Segura. Perfumería Triple C garantiza la seguridad transaccional de sus clientes.').style('flex-grow: 1; text-align: left;')
            ui.label('CUIT: 01-34567890-1 - Calle 1234, CABA.').style('flex-grow: 1; text-align: right;')


        with ui.row().style('width: 100%; background-color: #f1f1f1; padding: 20px; margin-top: 10px; border: 1px solid black;'):
            ui.label('© 2023 Triple C. Todos los derechos reservados.').style('flex-grow: 1; text-align: left;')
            ui.link('Política de Privacidad', '/privacy').style('margin-right: 20px;')
            ui.link('Términos de Servicio', '/terms').style('margin-right: 20px;')
            ui.link('Contacto', '/contacts').style('margin-right: 5px;')




@ui.page('/contacts')
def contacts_page():
    ui.add_head_html("""<style> body {background-image: url('/img/fondo.png'); background-size: cover;} </style>""")
    with ui.column().classes('absolute-center items-center'):
        ui.label('Contactos').style('font-size: 32px; font-weight: bold; margin-bottom: 20px; color: white;')
        with ui.card().classes('w-96 p-4 shadow-lg'):
            ui.label('Telefono de contacto: +54 91157540600').classes('w-full mb-3')
            ui.label('Mail de contacto: soporteclientetriplec@gmail.com').classes('w-full mb-3')
            ui.label('Contamos con atencion al cliente 24/7').classes('w-full mb-3')



# Vista Admin
@ui.page('/admin')
def admin_page():
    ui.add_head_html("""
        <style>
            body {
                background-image: url('/img/fondo.png');
                background-size: cover;
            }
            .marketing-title {
                font-size: 28px;
                font-weight: bold;
                color: #2d49ad;  
                margin-bottom: 10px;
            }
            .perfume-container {
                background-color: #ffffffcc;
                border-radius: 8px;
                padding: 15px 20px;
                margin: 10px;
                cursor: pointer;
                box-shadow: 0 1px 5px rgba(0, 0, 0, 0.15);
                transition: all 0.2s;
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
                width: 280px;
            }
            .perfume-container:hover {
                background-color: #f5f5f5;
                transform: translateY(-2px);
            }
            .perfume-name {
                font-size: 18px;
                font-weight: 600;
                color: #333;
                margin: 10px 0 5px 0;
                text-align: center;
            }
            .perfume-warning {
                font-size: 14px;
                color: #e53935;
                margin: 5px 0;
                text-align: center;
                font-weight: bold;
            }
            .perfume-grid {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 20px;
                max-width: 1200px;
                margin: 20px auto;
                padding: 0 15px;
            }
            .stock-info {
                font-size: 14px;
                margin: 5px 0;
                text-align: center;
            }
            .low-stock {
                color: red;
                font-weight: bold;
            }
            .normal-stock {
                color: green;
                font-weight: normal;
            }
            .admin-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                width: 100%;
                max-width: 1200px;
                margin: 0 auto;
                padding: 0 20px;
            }
        </style>
    """)

    with ui.column().classes('w-full items-center'):
        with ui.row().classes('admin-header'):
            ui.label('Gestión de Stock - Administrador').classes('marketing-title')
            with ui.row():
                ui.button('Ver como Cliente', on_click=lambda: ui.navigate.to('/products')).classes('bg-blue-600 text-white')
                ui.button('Cerrar Sesión', on_click=logout).classes('bg-red-700 text-white')

        data = get_products_from_supabase()
        if not data:
            ui.notify('No se pudieron cargar los productos.', type='negative')
            return

        with ui.element('div').classes('perfume-grid'):
            for product in data:
                with ui.card().classes('perfume-container'):
                    ui.image(product['imagenPerfume']).style('width: 100%; height: 200px; object-fit: cover; border-radius: 8px;')
                    ui.label(product['nombrePerfume']).classes('perfume-name')

                    capacities = [50, 70, 100]
                    low_stock = any(product.get(f'stock_{cap}ml', 0) < 10 for cap in capacities)

                    low_stock_label = ui.label('⚠️ Bajo stock').classes('perfume-warning')
                    if low_stock:
                        low_stock_label.style('display: block;')
                    else:
                        low_stock_label.style('display: none;')

                    stock_info = []
                    for cap in capacities:
                        stock = product.get(f'stock_{cap}ml', 0)
                        stock_class = 'low-stock' if stock < 10 else 'normal-stock'
                        stock_info.append(f"<span class='{stock_class}'>{cap}ml: {stock}</span>")
                    resumen_stock_label = ui.html(" | ".join(stock_info)).classes('stock-info')

                    with ui.dialog() as dialog, ui.card():
                        ui.label(f"Gestionar stock: {product['nombrePerfume']}").classes('text-lg font-bold')

                        for cap in capacities:
                            stock_key = f'stock_{cap}ml'
                            current_stock = product.get(stock_key, 0)
                            stock_class = 'low-stock' if current_stock < 10 else 'normal-stock'

                            with ui.row().classes('items-center justify-between w-full'):
                                stock_label = ui.label(f"Stock {cap}ml: {current_stock}").classes(f'stock-info {stock_class}')
                                cantidad_input = ui.number("", min=1, value=1).props('dense outlined').style('width: 70px;')

                                ui.button(
                                    "Agregar", 
                                    on_click=lambda cap=cap, inp=cantidad_input, p=product, lbl=stock_label, resumen=resumen_stock_label, low_label=low_stock_label: 
                                        actualizar_stock(p, cap, inp.value, lbl, resumen, low_label)
                                ).props('dense color=green')

                        ui.button("Cerrar", on_click=dialog.close).props('flat')

                    ui.button("Gestionar Stock", on_click=dialog.open).classes('w-full mt-2 bg-blue-600 text-white')


def actualizar_stock(product, capacity, cantidad, stock_label, resumen_label, low_stock_label):
    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            ui.notify("Cantidad debe ser mayor que 0", type='warning')
            return

        key = f"stock_{capacity}ml"
        result = supabase.table("perfumes").select("*").eq("id", product['id']).single().execute()

        if result.data:
            data_actualizada = result.data
            stock_actual = data_actualizada.get(key, 0)
            nuevo_stock = stock_actual + cantidad

            supabase.table("perfumes").update({key: nuevo_stock}).eq("id", product['id']).execute()

            ui.notify(f"Stock actualizado a {nuevo_stock} para {capacity}ml", type='positive')

            color_class = 'low-stock' if nuevo_stock < 10 else 'normal-stock'
            stock_label.set_text(f"Stock {capacity}ml: {nuevo_stock}")
            # Reemplazar clases para que no queden clases anteriores
            stock_label.classes(f'stock-info {color_class}')

            nuevo_resultado = supabase.table("perfumes").select("*").eq("id", product['id']).single().execute()
            if nuevo_resultado.data:
                data = nuevo_resultado.data
                capacidades = [50, 70, 100]
                resumen = []
                bajo_stock = False

                for cap in capacidades:
                    val = data.get(f"stock_{cap}ml", 0)
                    clase = 'low-stock' if val < 10 else 'normal-stock'
                    resumen.append(f"<span class='{clase}'>{cap}ml: {val}</span>")
                    if val < 10:
                        bajo_stock = True

                resumen_label.set_content(" | ".join(resumen))

                if bajo_stock:
                    low_stock_label.style('display: block;')
                else:
                    low_stock_label.style('display: none;')

        else:
            ui.notify("No se encontró el producto", type='negative')

    except Exception as e:
        ui.notify(f"Error al actualizar stock: {str(e)}", type='negative')


# Vista Marketing 
@ui.page('/marketing')
def marketing_page():
    ui.add_head_html("""
        <style>
            body {
                background-image: url('/img/fondo.png');
                background-size: cover;
            }
            .marketing-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                width: 100%;
                max-width: 1200px;
                margin: 0 auto 20px auto;
                padding: 0 20px;
            }
            .marketing-title {
                font-size: 28px;
                font-weight: bold;
                color: #2d49ad 
                margin-bottom: 10px;
            }
            .marketing-description {
                font-size: 18px;  
                color: #1e3178 ;
                margin-bottom: 20px;
                text-align: center;
            }
            .search-container {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 10px;
                margin-bottom: 20px;
                width: 100%;
            }
            .search-input {
                width: 300px;
            }
        </style>
    """)
    
    with ui.column().classes('w-full items-center'):
        with ui.row().classes('marketing-header'):
            ui.label('Gestión de Promociones').classes('marketing-title')
            with ui.row():
                ui.button('Ver como Cliente', on_click=lambda: ui.navigate.to('/products')).classes('bg-blue-600 text-white')
                ui.button('Cerrar Sesión', on_click=logout).classes('bg-red-700 text-white')

        ui.label('Visualizá los perfumes disponibles, aplicá o quitá descuentos y observá el precio actualizado en tiempo real.').classes('marketing-description')
        
        with ui.row().classes('search-container'):
            search_input = ui.input('Buscar perfume por nombre...').props('outlined').classes('search-input')
            ui.button('Buscar', on_click=lambda: filtrar_perfumes(search_input.value)).classes('bg-green-700 text-white')
            ui.button('Reestablecer', on_click=lambda: reset_search()).classes('bg-gray-500 text-white')

        perfumes_original = get_products_from_supabase()
        perfumes = perfumes_original.copy()
        container = ui.row().classes('flex flex-wrap justify-center gap-6')
        
        def filtrar_perfumes(texto):
            filtro = texto.lower().strip()
            nonlocal perfumes
            perfumes = [p for p in perfumes_original if filtro in p['nombrePerfume'].lower()]
            refresh_view()
        
        def reset_search():
            nonlocal perfumes
            search_input.value = ""
            perfumes = perfumes_original.copy()
            refresh_view()

        def update_discount(perfume_id, new_discount):
            try:
                supabase.table('perfumes').update({'descuento': int(new_discount)}).eq('id', perfume_id).execute()
                ui.notify(f'Descuento actualizado a {int(new_discount)}%', type='positive')
                nonlocal perfumes_original, perfumes
                perfumes_original = get_products_from_supabase()
                perfumes = perfumes_original.copy()
                refresh_view()
            except Exception as e:
                ui.notify(f"Error al actualizar descuento: {e}", type='negative')

        def refresh_view():
            container.clear()
            for perfume in perfumes:
                original_price = perfume['precioPerfume']
                discount = perfume.get('descuento', 0)
                final_price = original_price * (1 - discount / 100) if discount else original_price

                border_color = 'border: 3px solid green;' if discount > 0 else 'border: 1px solid #ccc;'
                with container:
                    with ui.card().style(f'width: 280px; padding: 16px; background: white; border-radius: 12px; {border_color} box-shadow: 0 4px 12px rgba(0,0,0,0.1);'):
                        ui.image(perfume['imagenPerfume']).style('width: 100%; height: 200px; object-fit: cover; border-radius: 8px;')
                        ui.label(perfume['nombrePerfume']).classes('text-lg font-bold mt-2')
                        ui.label(f'Marca: {perfume["marcaPerfume"]}').classes('text-sm text-gray-600')
                        ui.label(f'Aroma: {perfume["aromaPerfume"]}').classes('text-sm text-gray-600')
                        ui.label(f'Duración: {perfume["duracionPerfume"]}').classes('text-sm text-gray-600')

                        ui.label(f'Precio de lista: ${original_price:.2f}').classes('text-sm mt-2')
                        if discount > 0:
                            ui.label(f'Precio con descuento ({discount}%): ${final_price:.2f}').classes('text-sm text-green-700 font-bold')

                        input_discount = ui.number(label='Nuevo descuento (%)', value=discount, min=0, max=100).classes('w-full mt-2')
                        dynamic_price_label = ui.label(f'Precio actualizado: ${final_price:.2f}').classes('text-sm text-blue-800 font-bold')

                        def update_dynamic_price(e):
                            try:
                                d = float(e.value)
                                new_price = original_price * (1 - d / 100)
                                dynamic_price_label.text = f'Precio actualizado: ${new_price:.2f}'
                            except:
                                dynamic_price_label.text = 'Precio actualizado: --'

                        input_discount.on('input', update_dynamic_price)

                        with ui.row().classes('mt-3'):
                            ui.button('Aplicar', on_click=lambda p=perfume, i=input_discount: update_discount(p['id'], i.value)).classes('bg-green-600 text-white')
                            ui.button('Eliminar', on_click=lambda p=perfume: update_discount(p['id'], 0)).classes('bg-red-600 text-white')

        refresh_view()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(storage_secret='triplec')
