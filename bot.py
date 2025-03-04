import discord
import json
import os
from discord.ext import commands
from discord import TextChannel, VoiceChannel, CategoryChannel

# Configurando Intents
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True

# Criando o bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Pasta dos templates e backup
TEMPLATE_DIR = "templates"
BACKUP_FILE = "backup/backup.json"

# Função para salvar um backup do servidor
async def salvar_backup(guild):
    backup_data = {"roles": [], "channels": []}

    # Salvando cargos
    for role in guild.roles:
        if role.is_default():  # Ignorar o cargo @everyone
            continue
        backup_data["roles"].append({
            "name": role.name,
            "color": str(role.color),
            "permissions": str(role.permissions.value)
        })

    # Salvando canais
    for channel in guild.channels:
        backup_data["channels"].append({
            "name": channel.name,
            "type": "text" if isinstance(channel, discord.TextChannel) else "voice" if isinstance(channel, discord.VoiceChannel) else "category"
        })

    # Criando pasta de backup se não existir
    os.makedirs(os.path.dirname(BACKUP_FILE), exist_ok=True)

    # Salvando em JSON
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, indent=4)

    print("Backup do servidor salvo!")

# Comando para aplicar um template
@bot.command()
async def template(ctx, nome_template):
    template_path = os.path.join(TEMPLATE_DIR, f"{nome_template}.json")

    # Verifica se o template existe
    if not os.path.exists(template_path):
        await ctx.send(f"❌ Template `{nome_template}` não encontrado.")
        return

    # Carrega o template
    with open(template_path, "r", encoding="utf-8") as f:
        template_data = json.load(f)

    guild = ctx.guild

    # Salvar backup antes de modificar o servidor
    await salvar_backup(guild)

    # Criar categorias e canais dentro delas
    created_channels = []  # Para garantir que apenas os novos canais sejam apagados
    created_voice_channels = []  # Para registrar os canais de voz criados
    created_categories = []  # Para registrar as categorias criadas

    for category in template_data["channels"]:
        if category["type"] == 4:  # Se for uma categoria
            new_category = await guild.create_category(category["name"])
            created_categories.append(new_category)
            await ctx.send(f"✅ Categoria `{category['name']}` criada.")

            # Criar canais dentro da categoria
            for channel in category.get("channels", []):
                if channel["type"] == 0:  # Canal de texto
                    new_channel = await guild.create_text_channel(channel["name"], category=new_category)
                    created_channels.append(new_channel)
                elif channel["type"] == 2:  # Canal de voz
                    # Verificar se a categoria "╔═•【VOZ】•═╗" existe ou criar ela
                    voice_category = discord.utils.get(guild.categories, name="╔═•【VOZ】•═╗")
                    if not voice_category:
                        voice_category = await guild.create_category("╔═•【VOZ】•═╗")

                    new_voice_channel = await guild.create_voice_channel(
                        channel["name"], 
                        category=voice_category,  # Define a categoria para o canal de voz
                        user_limit=channel.get("user_limit", 0)
                    )
                    created_voice_channels.append(new_voice_channel)
                    await ctx.send(f"✅ Canal de voz `{channel['name']}` criado na categoria `{voice_category.name}`.")

    # Criar cargos
    created_roles = []
    for role in template_data["roles"]:
        try:
            new_role = await guild.create_role(
                name=role["name"],
                colour=discord.Colour(int(role["color"].strip("#"), 16)),
                permissions=discord.Permissions(int(role["permissions"]))
            )
            created_roles.append(new_role)
            await ctx.send(f"✅ Cargo `{role['name']}` criado.")
        except discord.Forbidden:
            print(f"Sem permissão para criar o cargo {role['name']}.")

    # Apagar categorias antigas
    for category in guild.categories:
        if category not in created_categories:  # Verifica se a categoria não foi criada pelo template
            try:
                await category.delete()
                print(f"Categoria {category.name} deletada.")
            except discord.Forbidden:
                print(f"Sem permissão para deletar a categoria {category.name}.")

    # Apagar canais antigos (exceto os recém criados)
    for channel in guild.channels:
        if isinstance(channel, (TextChannel, VoiceChannel)):  # Verifica se é um canal de texto ou voz
            if channel not in created_channels and channel not in created_voice_channels:  # Verifica se o canal não foi criado pelo template
                try:
                    await channel.delete()
                    print(f"Canal {channel.name} deletado.")
                except discord.Forbidden:
                    print(f"Sem permissão para deletar o canal {channel.name}.")

    # Apagar cargos antigos após os novos serem criados
    for role in guild.roles:
        if role not in created_roles and not role.is_default():
            try:
                await role.delete()
                print(f"Cargo {role.name} deletado.")
            except discord.Forbidden:
                print(f"Sem permissão para deletar o cargo {role.name}.")

    await ctx.send(f"✅ Template `{nome_template}` aplicado com sucesso!")

# Comando para enviar um template em formato de texto
@bot.command()
async def criar_template(ctx):
    # Perguntar o nome do template
    await ctx.send("🔧 Qual o nome do template?")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    # Esperar pela resposta do nome do template
    nome_msg = await bot.wait_for("message", check=check)
    nome_template = nome_msg.content.strip()

    # Perguntar pelo conteúdo do template
    await ctx.send("🔧 Envie o conteúdo do template (em formato JSON).")

    # Esperar pela resposta do conteúdo do template
    json_msg = await bot.wait_for("message", check=check)
    json_content = json_msg.content.strip()

    try:
        # Tentar carregar o conteúdo como JSON
        template_data = json.loads(json_content)
    except json.JSONDecodeError:
        await ctx.send("❌ O formato JSON enviado é inválido.")
        return

    # Salvar o template no arquivo
    template_path = os.path.join(TEMPLATE_DIR, f"{nome_template}.json")
    
    # Criar a pasta de templates se não existir
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    
    # Salvar o template
    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(template_data, f, indent=4)
    
    await ctx.send(f"✅ Template `{nome_template}` salvo com sucesso!")

# Iniciar o bot
bot.run(os.getenv('DISCORD_TOKEN'))
