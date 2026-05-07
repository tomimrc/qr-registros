# # app/routers/qr.py

# from fastapi import APIRouter, Depends, HTTPException
# from fastapi.responses import StreamingResponse, HTMLResponse
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.database import get_db
# from app.models.tenant import Tenant
# from app.core.config import settings
# import qrcode
# import qrcode.image.svg
# import uuid
# import io

# router = APIRouter()


# @router.get("/{tenant_id}/png")
# async def get_qr_png(
#     tenant_id: uuid.UUID,
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Devuelve el QR como imagen PNG lista para mostrar o imprimir.
#     Uso: GET /qr/{tenant_id}/png
#     """
#     # Validar que el tenant existe
#     tenant = await db.get(Tenant, tenant_id)
#     if not tenant or not tenant.is_active:
#         raise HTTPException(status_code=404, detail="Empresa no encontrada.")

#     # La URL que va encodada en el QR
#     # En producción esto sería tu dominio real
#     url = f"{settings.BASE_URL}/app?tenant_id={tenant_id}"

#     # Generar el QR
#     qr = qrcode.QRCode(
#         version=1,              # Tamaño del QR (1=pequeño, 40=grande)
#         error_correction=qrcode.constants.ERROR_CORRECT_H,  # Alta tolerancia a daños
#         box_size=10,            # Píxeles por celda
#         border=4,               # Margen en celdas
#     )
#     qr.add_data(url)
#     qr.make(fit=True)           # Ajusta el tamaño automáticamente

#     # Convertir a imagen PNG en memoria (sin guardar en disco)
#     img = qr.make_image(fill_color="black", back_color="white")
#     buffer = io.BytesIO()
#     img.save(buffer, format="PNG")
#     buffer.seek(0)

#     # Devolver como stream de bytes
#     return StreamingResponse(
#         buffer,
#         media_type="image/png",
#         headers={
#             # Esto hace que el navegador lo descargue como archivo
#             "Content-Disposition": f"inline; filename=qr-{tenant.slug}.png"
#         }
#     )


# @router.get("/{tenant_id}/print")
# async def get_qr_print(
#     tenant_id: uuid.UUID,
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Devuelve una página HTML lista para imprimir con el QR y el nombre del local.
#     Uso: GET /qr/{tenant_id}/print → abrir en navegador → Ctrl+P
#     """
#     tenant = await db.get(Tenant, tenant_id)
#     if not tenant or not tenant.is_active:
#         raise HTTPException(status_code=404, detail="Empresa no encontrada.")

#     # URL de la imagen del QR (el endpoint de arriba)
#     qr_url = f"{settings.BASE_URL}/qr/{tenant_id}/png"
#     app_url = f"{settings.BASE_URL}/app?tenant_id={tenant_id}"

#     html = f"""
#     <!DOCTYPE html>
#     <html lang="es">
#     <head>
#         <meta charset="UTF-8">
#         <title>QR - {tenant.name}</title>
#         <style>
#             * {{ margin: 0; padding: 0; box-sizing: border-box; }}
#             body {{
#                 font-family: Arial, sans-serif;
#                 display: flex;
#                 justify-content: center;
#                 align-items: center;
#                 min-height: 100vh;
#                 background: white;
#             }}
#             .card {{
#                 text-align: center;
#                 padding: 40px;
#                 border: 3px solid #000;
#                 border-radius: 16px;
#                 max-width: 400px;
#                 width: 100%;
#             }}
#             h1 {{ font-size: 28px; margin-bottom: 8px; }}
#             p {{ color: #666; margin-bottom: 24px; font-size: 14px; }}
#             img {{ width: 280px; height: 280px; }}
#             .footer {{ margin-top: 24px; font-size: 12px; color: #999; }}
#             @media print {{
#                 body {{ background: white; }}
#                 .card {{ border: 2px solid #000; }}
#             }}
#         </style>
#     </head>
#     <body>
#         <div class="card">
#             <h1>{tenant.name}</h1>
#             <p>Escaneá para registrar tu asistencia</p>
#             <img src="{qr_url}" alt="QR Code" />
#             <div class="footer">
#                 <p>Sistema de Asistencia</p>
#             </div>
#         </div>
#     </body>
#     </html>
#     """
#     return HTMLResponse(content=html)