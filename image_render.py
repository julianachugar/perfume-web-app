#Script en Python para descargar imágenes desde URLs. Cada imagen se descargo y guardo como un archivo PNG en el sistema.
#se convirtio cada imagen PNG a formato SVG (Scalable Vector Graphics), que es un formato de imagen basado en vectores. 
# las imágenes en formato PNG se guardan localmente en la misma carpeta donde se ejecuta el script. Cada imagen se nombra de acuerdo con el nombre del perfume
# los archivos SVG también se almacenan en la misma carpeta

#PNG: Las imágenes originales se guardan localmente como archivos PNG.
# SVG: Se crean archivos SVG que contienen las imágenes en formato Base64.
# Uso de Base64: La codificación en Base64 se usa únicamente para incrustar las imágenes PNG dentro del archivo SVG.
# CairoSVG y CairoCFFI. Para utilizarlos descargamos MSYS2 (herramientas y bibliotecas para compilar y ejecutar aplicaciones en Windows)

import os
import requests
import base64

class ImageRender:
    """Clase encargada de la descarga y conversión de imágenes a formato SVG."""

    @staticmethod
    def download_and_convert_image(url, svg_name):
        """Descarga una imagen de una URL y la convierte a formato SVG."""
        try:
            
            if url.startswith('data:image'):
                
                header, encoded = url.split(',', 1)
              
                png_data = base64.b64decode(encoded)
                if not png_data:
                    raise ValueError("Los datos de la imagen decodificada están vacíos.")
                
           
                ImageRender.create_svg_with_image(svg_name, png_data)
            else:

                response = requests.get(url)
                if response.status_code == 200:
                    
                    if not response.content:
                        raise ValueError("La imagen descargada está vacía.")
                    
                    
                    ImageRender.create_svg_with_image(svg_name, response.content)
                else:
                    print(f"Error al descargar la imagen: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión al intentar descargar la imagen: {e}")
        except Exception as e:
            print(f"Error al procesar la imagen: {e}")

    @staticmethod
    def create_svg_with_image(svg_name, png_data):
        """Crea un archivo SVG que incluye la imagen PNG en formato base64."""
        try:
           
            encoded_png_data = base64.b64encode(png_data).decode('utf-8')

            
            svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
                <image href="data:image/png;base64,{encoded_png_data}" width="200" height="200"/>
            </svg>"""

            
            with open(f'{svg_name}.svg', 'w') as svg_file:
                svg_file.write(svg_content)
            
            print(f"Imagen {svg_name}.svg creada con éxito.")
        except Exception as e:
            print(f"Error al crear el archivo SVG: {e}")


api_url = 'https://66ec94f02b6cf2b89c5ed519.mockapi.io/perfumeria/Productos'


try:
    response = requests.get(api_url)
    if response.status_code == 200:
        productos = response.json() 


        for producto in productos:
            url_imagen = producto['imagenPerfume']
            nombre_svg = producto['nombrePerfume'].replace(" ", "_")  
            ImageRender.download_and_convert_image(url_imagen, nombre_svg)
    else:
        print(f"Error al obtener los datos de la API: {response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"Error de conexión al intentar acceder a la API: {e}")
