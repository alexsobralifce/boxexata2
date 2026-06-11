from typing import Any
from src.domain.repositories.i_message_gateway import IMessageGateway
from src.domain.repositories.i_property_repository import IPropertyRepository
from src.shared.logger import logger

async def send_property_cards(
    phone: str,
    slice_results: list[dict[str, Any]],
    start_num: int,
    property_repo: IPropertyRepository,
    message_gateway: IMessageGateway,
) -> None:
    """Envia cartões de imóveis formatados com imagens e emojis para o WhatsApp do usuário."""
    for idx, item in enumerate(slice_results):
        num = start_num + idx
        property_id = item.get("id")
        
        # Carrega detalhes completos do imóvel
        detailed = None
        if property_id:
            try:
                detailed = await property_repo.find_by_id(property_id)
            except Exception as e:
                logger.error("Erro ao carregar detalhes para envio de cartões", property_id=property_id, error=str(e))
        
        # Prepara dados formatados
        price_val = item.get("value") or (detailed.value.amount if detailed else 0.0)
        price_fmt = (
            f"R$ {price_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        
        ref = item.get("ref") or (detailed.ref if detailed else "N/A")
        address = detailed.address if detailed else item.get("address", "N/A")
        neighborhood = detailed.neighborhood if detailed else item.get("neighborhood", "N/A")
        url = item.get("url") or (detailed.url if detailed else "")
        
        # Características do imóvel
        features_list = detailed.features if (detailed and detailed.features) else []
        features_text = ""
        if features_list:
            # Pega no máximo as 6 primeiras características para não alongar muito o card
            features_text = "\n".join(f"- {f}" for f in features_list[:6])
        else:
            basic_features = item.get("features", [])
            if basic_features:
                features_text = "\n".join(f"- {f}" for f in basic_features[:6])
            else:
                features_text = "- Informações sobre cômodos/características não detalhadas."

        # Proximidade a pontos de referência
        proximity_text = ""
        if item.get("proximity"):
            proximity_text = f"📍 *Proximidade*: {item.get('proximity')}\n"

        # Constrói o texto do card com emojis
        card_text = (
            f"🏡 *{num}. {item.get('property_type', 'Imóvel')} no bairro {neighborhood}*\n\n"
            f"💰 *Valor*: {price_fmt}\n"
            f"🆔 *Ref*: {ref}\n"
            f"📍 *Endereço*: {address}\n"
            f"🏢 *Bairro*: {neighborhood}\n"
            f"{proximity_text}"
            f"✨ *Características / Descrição*:\n{features_text}\n\n"
            f"🔗 *Link para fotos e site*: {url}"
        )
        
        # Determina fotos a enviar
        photos = detailed.photos if (detailed and detailed.photos) else item.get("photos", [])
        if not photos and item.get("cover_image"):
            photos = [item["cover_image"]]
            
        cover_photo = photos[0] if photos else None
        
        # Envia imagem
        if cover_photo:
            try:
                await message_gateway.send_image(
                    phone,
                    cover_photo,
                    f"Imóvel {num} - Ref {ref}"
                )
            except Exception as ex:
                logger.warning(
                    "Erro ao enviar foto do imóvel no card",
                    url=cover_photo,
                    error=str(ex)
                )
        
        # Envia texto
        await message_gateway.send_text(phone, card_text)
