#!/usr/bin/env python
import asyncio
import sys
from src.shared.container import get_container
from src.shared.context import set_current_broker


async def main() -> None:
    print("🚀 Iniciando script de sincronização detalhada de imóveis...")
    container = get_container()
    property_repo = container["property_repo"]
    broker_repo = container["broker_repo"]

    # 1. Carrega e ativa o primeiro broker profile no contexto
    try:
        brokers = await broker_repo.list_all()
        if brokers:
            active_broker = brokers[0]
            set_current_broker(active_broker)
            print(
                f"ℹ️ Corretor ativo configurado: {active_broker.broker_name} "
                f"| URL: {active_broker.site_base_url} (Normalizada para: {property_repo.site_base_url})"
            )
        else:
            print(
                f"⚠️ Nenhum Perfil de Corretor encontrado no banco. "
                f"Usando URL padrão das configurações: {property_repo.site_base_url}"
            )
    except Exception as e:
        print(f"❌ Erro ao listar perfis de corretores: {e}")
        sys.exit(1)

    # 2. Busca a listagem básica
    print("⏳ Buscando listagem básica de imóveis no site...")
    try:
        basics = await property_repo._scrape_all_basic_listings()
        total_items = len(basics)
        print(f"✅ Encontrados {total_items} imóveis na listagem básica.")
    except Exception as e:
        print(f"❌ Erro ao buscar listagem básica de imóveis: {e}")
        sys.exit(1)

    if total_items == 0:
        print("ℹ️ Nenhum imóvel encontrado para processar.")
        return

    # 3. Itera em cada imóvel para buscar detalhes, comodos e fotos completas
    success_count = 0
    error_count = 0

    print(
        "⏳ Iniciando raspagem de detalhes para cada imóvel (isso pode demorar devido ao delay de segurança)..."
    )
    for idx, (pid, basic) in enumerate(basics.items(), 1):
        ref = basic.get("ref", "Sem REF")
        print(f"🔄 [{idx}/{total_items}] Processando código={pid} (REF={ref})...")
        try:
            url = f"{property_repo.site_base_url}/detalhe_imovel.php?codigo={pid}"
            html = await property_repo._fetch_html(url)
            listing = await property_repo._parse_detail_html(pid, html, basic)

            if listing:
                # Salva/atualiza no banco de dados (upsert)
                await property_repo.save(listing)

                # Limpa cache do detalhe correspondente
                cache_key = f"property_detail_{pid}"
                await property_repo.cache.delete(cache_key)

                # Mostra detalhes atualizados
                photos_count = len(listing.photos)
                print(
                    f"   ✅ Sucesso! Quartos: {listing.bedrooms or 0} "
                    f"| Banheiros: {listing.bathrooms or 0} "
                    f"| Vagas: {listing.parking_spaces or 0} "
                    f"| Fotos: {photos_count} "
                    f"| Descrição: {len(listing.description or '')} caracteres"
                )
                success_count += 1
            else:
                print(f"   ⚠️ Detalhes não retornados para o imóvel {pid}")
                error_count += 1
        except Exception as ex:
            print(f"   ❌ Erro ao raspar imóvel código={pid}: {ex}")
            error_count += 1

    print("\n==================================================")
    print("🎉 Processo concluído!")
    print(f"👉 Total processado: {total_items}")
    print(f"👉 Atualizados com sucesso: {success_count}")
    print(f"👉 Erros/Falhas: {error_count}")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
