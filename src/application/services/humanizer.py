from datetime import datetime, timezone, timedelta
import random

# Brasília timezone (UTC-3), Sobral CE does not have Daylight Saving Time
BRASILIA_TZ = timezone(timedelta(hours=-3))


def get_greeting() -> str:
    """Retorna 'Bom dia', 'Boa tarde' ou 'Boa noite' com emoji baseado na hora atual (UTC-3)."""
    # 05–11h → Bom dia ☀️
    # 12–17h → Boa tarde 🌤️
    # 18–04h → Boa noite 🌙
    dt = datetime.now(tz=BRASILIA_TZ)
    hour = dt.hour
    if 5 <= hour < 12:
        return "☀️ Bom dia"
    elif 12 <= hour < 18:
        return "🌤️ Boa tarde"
    else:
        return "🌙 Boa noite"


def get_welcome_first_time_phrase(bot_name: str, broker_name: str) -> str:
    """Frase aleatória para o primeiro contato/boas-vindas solicitando o nome."""
    greeting = get_greeting()
    lgpd_note = "_Seus dados são usados apenas para seu atendimento, conforme nossa Política de Privacidade._"
    variations = [
        f"{greeting}! 😊\n\nAqui é a {bot_name}, atendente virtual da {broker_name}.\n\nFico feliz em te atender! Para que eu possa te ajudar melhor, qual é o seu nome?\n\n{lgpd_note}",
        f"{greeting}! Que bom ter você por aqui. 😊\n\nEu sou a {bot_name}, a assistente virtual da {broker_name}.\n\nPara que eu possa falar com você da melhor forma, me diz: qual o seu nome?\n\n{lgpd_note}",
        f"{greeting}! Seja muito bem-vindo(a). 😊\n\nAqui quem fala é a {bot_name}, da {broker_name}.\n\nComo posso te chamar? Me conta seu nome para eu iniciar seu atendimento!\n\n{lgpd_note}",
    ]
    return random.choice(variations)


def get_welcome_returning_phrase(client_name: str | None, bot_name: str, broker_name: str) -> str:
    """Frase aleatória para cliente que retorna."""
    greeting = get_greeting()
    nome = client_name or "amigo(a)"
    variations = [
        f"{greeting}, {nome}! Que prazer ter você aqui novamente! 😊\n\nAqui é a {bot_name}, da {broker_name}.\n\nVocê gostaria de buscar um imóvel para **Locação** ou para **Venda**?",
        f"{greeting}, {nome}! 😊 Que bom te ver de novo por aqui na {broker_name}!\n\nEstou pronta para te ajudar. Vamos buscar um imóvel para **Locação** ou **Venda**?",
        f"{greeting}! Olá, {nome}, que alegria falar com você novamente! 😊\n\nEu, {bot_name}, estou aqui para te ajudar. Você gostaria de buscar um imóvel para **Locação** ou para **Venda**?",
    ]
    return random.choice(variations)


def get_welcome_name_confirmation_phrase(client_name: str | None) -> str:
    """Confirmação do nome do cliente."""
    nome = client_name or "amigo(a)"
    variations = [
        f"Prazer, {nome}! 😊",
        f"Que prazer falar com você, {nome}! 😊",
        f"Muito prazer, {nome}! Fico feliz em falar com você. 😊",
    ]
    return random.choice(variations)


def get_intent_recognized_phrase(client_name: str | None, intent: str) -> str:
    """Confirmação da intenção (Locação/Venda)."""
    nome = client_name or "amigo(a)"
    intent_action = "locação" if "loca" in intent.lower() or "alug" in intent.lower() else "venda"
    variations = [
        f"Perfeito, {nome}! Deixa eu pesquisar as melhores opções de {intent_action} pra você 🏡🔍",
        f"Excelente escolha, {nome}! Vou buscar agora mesmo as melhores oportunidades de {intent_action} para você! 🚀",
        f"Ótimo, {nome}! Estou vasculhando nossa base em busca das melhores opções de {intent_action} para você. 📂✨",
    ]
    return random.choice(variations)


def get_intent_invalid_phrase(client_name: str | None) -> str:
    """Mensagem de erro para intent inválido."""
    nome = client_name or "amigo(a)"
    variations = [
        f"Por favor, {nome}, digite **Locação** se você deseja alugar ou **Venda** se deseja comprar um imóvel.",
        f"Ops, {nome}! Não consegui identificar o que você procura. Digite **Locação** para alugar ou **Venda** para comprar.",
        f"Poderia me confirmar, {nome}? Você quer **Locação** (aluguel) ou **Venda** (compra)? Digite uma das opções!",
    ]
    return random.choice(variations)


def get_thinking_phrase(client_name: str | None = None) -> str:
    """Frase aleatória de espera e processamento."""
    nome = f", {client_name}" if client_name else ""
    variations = [
        f"Um momentinho{nome}... Vou pesquisar agora mesmo! 🔍",
        f"Deixa eu dar uma olhada rápida no que temos disponível pra você{nome}... ⏳",
        f"Já estou vasculhando nossa base de dados, segura aí um segundinho{nome}! 😊",
        f"Buscando com carinho as melhores opções pra você{nome}... 🏠✨",
    ]
    return random.choice(variations)


def get_search_success_phrase(client_name: str | None = None) -> str:
    """Frase aleatória de sucesso na busca."""
    nome = f", {client_name}" if client_name else ""
    variations = [
        f"Encontrei esses imóveis que encaixam nas suas preferências{nome}! 🏡✨👇",
        f"Olha o que encontrei pra você{nome}! 🎉🏡",
        f"Eba! Encontrei ótimas opções pra você{nome}! 😊👇",
        f"Aqui estão as melhores opções dentro do perfil que você me pediu{nome}! ✨👇",
    ]
    return random.choice(variations)


def get_not_found_phrase(
    client_name: str | None, property_type: str, location: str, max_value: float | None = None
) -> str:
    """Mensagem empática quando nenhum imóvel é encontrado."""
    nome = client_name or "amigo(a)"
    tipo = property_type.lower() if property_type else "imóvel"
    loc = f" {location}" if location else ""

    val_info = ""
    if max_value:
        price_fmt = f"R$ {max_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        val_info = f" com valor até {price_fmt}"

    variations = [
        f"Não encontrei nenhuma opção de {tipo} para {loc}{val_info} no momento. 😔\n\n"
        f"Quer que eu te avise assim que novos imóveis com esse perfil surgirem no site? Digite **alertar** para ativar. 🔔\n"
        f"Se preferir fazer uma nova busca com outros critérios, digite **começar**.",
        f"Poxa, {nome}, não encontrei nada de {tipo} {loc}{val_info} no momento. 😔\n\n"
        f"Mas não desanime! Posso te avisar assim que novos imóveis com esse perfil surgirem no site. Digite **alertar** para ativar. 🔔\n"
        f"Se preferir tentar com outros critérios, digite **começar**! 😊",
        f"Hum, {nome}... No momento não temos nenhuma opção de {tipo} disponível para {loc}{val_info}. 😔\n\n"
        f"Deseja assinar nossos alertas para ser avisado(a) assim que entrar algo? Digite **alertar**! 🔔\n"
        f"Se quiser tentar uma busca diferente, basta digitar **começar**. 😉",
    ]
    return random.choice(variations)


def get_error_phrase() -> str:
    """Frase de erro técnico amigável e empática."""
    variations = [
        "Desculpe, tive um problema ao pesquisar no site da Exata Serviços no momento. 😔 Por favor, tente novamente em alguns instantes.",
        "Puxa, tive um pequeno imprevisto técnico aqui! 😅 Me dá mais um segundinho e tente novamente, por favor.",
        "Ops! Parece que deu um erro do meu lado. 😓 Pode tentar de novo? Se persistir, já já eu volto ao normal!",
    ]
    return random.choice(variations)


def get_solicitude_footer() -> str:
    """Footer solícito para o final de interações importantes."""
    variations = [
        "Precisa de mais alguma coisa? Estou aqui! 😊",
        "Se tiver dúvidas, pode me perguntar à vontade! 😄",
        "Posso te ajudar com mais alguma coisa? 😊",
        "Quer ajuda com algo mais? Fique à vontade para perguntar! ✨",
    ]
    return random.choice(variations)


def get_alert_activated_phrase(
    client_name: str | None,
    property_type: str,
    neighborhood: str,
    intent: str,
    max_value: float | None = None,
) -> str:
    """Mensagem de alerta ativado com entusiasmo."""
    nome = client_name or "amigo(a)"
    tipo = property_type or "imóvel"
    bairro = neighborhood or "Região selecionada"
    intent_lbl = "Locação" if "loca" in intent.lower() or "alug" in intent.lower() else "Venda"

    val_info = ""
    if max_value:
        price_fmt = f"R$ {max_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        val_info = f" até *{price_fmt}*"

    variations = [
        f"Perfeito, {nome}! ✅ Assinatura de alertas ativada. Vou te avisar "
        f"assim que surgirem novos imóveis do tipo *{tipo}* no bairro *{bairro}* "
        f"para *{intent_lbl}*{val_info}.\n\n"
        f"Para cancelar os alertas a qualquer momento, basta digitar 'desativar alerta'.",
        f"Tudo certo, {nome}! ✅ Cadastrei seu alerta com sucesso. "
        f"Vou ficar de olho! Quando entrar um(a) *{tipo}* no bairro *{bairro}* "
        f"para *{intent_lbl}*{val_info}, eu venho correndo te avisar! 🔔😊\n\n"
        f"Para remover esse alerta, basta digitar **desativar alerta**.",
    ]
    return random.choice(variations)


def get_alert_cancelled_phrase() -> str:
    """Mensagem de alerta cancelado com gentileza."""
    variations = [
        "Seus alertas de novos imóveis foram cancelados com sucesso. "
        "Se precisar de novos alertas no futuro, basta realizar uma busca e digitar 'alertar'.",
        "Tudo bem! Seus alertas foram cancelados com sucesso. 😊 "
        "Se precisar de mim novamente, estarei aqui!",
        "Alertas desativados com sucesso! Se mudar de ideia ou quiser buscar outras opções, estarei aqui à sua disposição. ✨",
    ]
    return random.choice(variations)


def get_unknown_command_phrase() -> str:
    """Mensagem de comando não reconhecido amigável."""
    variations = [
        "Não entendi. Por favor, digite o número do imóvel desejado (ex: 1, 2, 3), "
        "'mais' para ver mais opções, 'alertar' para receber alertas de novos imóveis, ou 'reiniciar' para começar uma nova busca.",
        "Hmm, não entendi direito. 😅 Você pode digitar o número do imóvel, 'mais', 'alertar' ou 'reiniciar'!",
    ]
    return random.choice(variations)


def get_no_more_results_phrase() -> str:
    """Mensagem de nenhum resultado adicional mais humanizada."""
    variations = [
        "Não encontrei mais imóveis com essas preferências no site. 😔 Digite 'reiniciar' para fazer uma nova busca. 🔄",
        "Olha, vasculhei tudo, mas essas foram todas as opções que encontramos com esse perfil. 🏡 "
        "Que tal reiniciar a busca com outros critérios? É só digitar 'reiniciar'! 🔄",
    ]
    return random.choice(variations)


def get_booking_phrase(ref: str = "") -> str:
    """Mensagem solícita e calorosa ao redirecionar para agendamento."""
    ref_info = f" para o imóvel Ref {ref}" if ref else ""
    wa_link = f"https://wa.me/558836113000?text=Olá,%20gostaria%20de%20agendar%20uma%20visita{ref_info.replace(' ', '%20')}"

    variations = [
        f"Com certeza posso te ajudar! 😊 Clique abaixo para falar diretamente com um dos nossos corretores. Eles adoram atender!\n\n"
        f"{wa_link}\n\n"
        f"Ou ligue para o telefone fixo: (88) 3611-3000.\n\n"
        f"Digite 'voltar' para retornar à lista de imóveis ou 'reiniciar' para fazer uma nova busca.",
        f"Excelente! Para agendar uma visita ou falar com um corretor, clique no link abaixo. Estamos prontos para te receber! 🏡✨\n\n"
        f"{wa_link}\n\n"
        f"Ou se preferir, ligue para: (88) 3611-3000.\n\n"
        f"Digite 'voltar' para retornar à lista de imóveis ou 'reiniciar' para fazer uma nova busca.",
    ]
    return random.choice(variations)


def get_farewell_question_phrase(client_name: str | None = None) -> str:
    """Pergunta profissional e amigável se o cliente precisa de mais ajuda, após criar um alerta."""
    nome = f", {client_name}" if client_name else ""
    variations = [
        f"Posso te ajudar com mais alguma coisa{nome}? 😊\n\n"
        "*1️⃣ - Sim*, quero continuar\n"
        "*2️⃣ - Não*, pode encerrar",
        f"Fico feliz em ter ajudado{nome}! 🎉 Tem mais alguma coisa em que eu possa te ajudar?\n\n"
        "*1️⃣ - Sim*, quero continuar\n"
        "*2️⃣ - Não*, pode encerrar",
        f"Tudo certo{nome}! 👍 Posso fazer mais alguma coisa por você?\n\n"
        "*1️⃣ - Sim*, quero continuar\n"
        "*2️⃣ - Não*, pode encerrar",
    ]
    return random.choice(variations)


def get_farewell_goodbye_phrase(client_name: str | None = None) -> str:
    """Mensagem de despedida calorosa ao encerrar o atendimento."""
    nome = f", {client_name}" if client_name else ""
    variations = [
        f"Foi um prazer te atender{nome}! 😊🏡\n"
        "Estarei sempre aqui caso precise de algo. Até logo e boas buscas! 🌟",
        f"Obrigada pela preferência{nome}! 🏡✨\n"
        "Se precisar de qualquer coisa, é só chamar. Até a próxima! 😊",
        f"Fico feliz em ter ajudado{nome}! 😊\n"
        "Qualquer dúvida ou nova busca, estarei aqui. Até logo! 👋",
    ]
    return random.choice(variations)


def get_farewell_invalid_option_phrase() -> str:
    """Mensagem quando o cliente digita algo fora de 1 ou 2 no estado FAREWELL."""
    variations = [
        "Por favor, escolha uma das opções:\n\n*1️⃣ - Sim*, quero continuar\n*2️⃣ - Não*, pode encerrar",
        "Não entendi. 😅 Responda apenas:\n\n*1* para continuar\n*2* para encerrar",
    ]
    return random.choice(variations)
