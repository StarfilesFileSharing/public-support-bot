import asyncio
import traceback
import requests

import datetime
import os
import subprocess

import ast
from textwrap import wrap

import discord
from discord.ext import tasks, pages, commands
from discord import option

import config

token = config.BOT_TOKEN

bot = discord.Bot(command_prefix="!", intents=discord.Intents.all())

@tasks.loop(seconds=60)
async def update_status():
	guild_count = len(bot.guilds)
	user_count = sum(guild.member_count for guild in bot.guilds)
	status_message = f"{guild_count} servers & {user_count} users"
	await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status_message))


@bot.event
async def on_message(message: discord.Message):

	if message.author.bot:
		return


@bot.event
async def on_ready():
	print("Bot startup completed")


@bot.slash_command()
async def ping(ctx):
	await ctx.respond("Pong!")


def sizeof_fmt(num, suffix="B"):
	for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
		if abs(num) < 1024.0:
			return f"{num:3.1f}{unit}{suffix}"
		num /= 1024.0
	return f"{num:.1f}Yi{suffix}"


@bot.slash_command(guild_ids=[648551503891791912])
@option(
	"attachment",
	discord.Attachment,
	description="A file to attach to the message",
	required=True,
)
async def upload(ctx, attachment: discord.Attachment):
	await ctx.defer()
	await attachment.save(f"{attachment.filename}")

	print("Uploading file:", attachment.filename)
	headers = {"User-Agent": "SignTunes discord bot"}

	response = requests.post(
			f"http://upload.starfiles.co/file",
			files={"upload": (attachment.filename, open(attachment.filename, "rb"))},
			headers=headers,
		)

	if response.ok:
			response = response.json()
			bbb = requests.get(
				"https://api.starfiles.co/file/fileinfo/" + response["file"], headers=headers
			)
			embed = discord.Embed(
				title=f"{attachment.filename}",
				color=0x00FF00,
				timestamp=datetime.datetime.utcnow(),
			)
			embed.url = "https://starfiles.co/file/" + response["file"]
			embed.set_author(name="New file uploaded")
			embed.add_field(
				name=f"Size: {str(sizeof_fmt(attachment.size))}													   "
					 + "\u200b",
				value=f'https://sts.st/u/{response["file"]}',
				inline=False,
			)
			embed.set_thumbnail(
				url=f'https://cdn.starfiles.co/file/icon/{response["file"]}'
			)
			await ctx.respond(embed=embed)
			os.remove(attachment.filename)
			return

	else:
		print(response.text)
		os.remove(attachment.filename)
		await ctx.respond("Failed to upload file, error: " + response.text)
		return

def human_format(num):
	magnitude = 0
	while abs(num) >= 1000:
		magnitude += 1
		num /= 1000.0
	return "%.0f%s" % (num, ["", "K", "M", "G", "T", "P"][magnitude])


class SearchView(discord.ui.View):
	def __init__(self):
		super().__init__()
		self.value = 0
		self.chosen = 0

	def get_response(self, response, triggerer):
		self.response = response
		self.owner = triggerer

	@discord.ui.button(label="Back", style=discord.ButtonStyle.green)
	async def back(self, button: discord.ui.Button, interaction: discord.Interaction):
		await interaction.response.defer()
		if interaction.user.id != self.owner:
			await interaction.followup.send_message(
				"You are not allowed to do this", ephemeral=True
			)
			return

		if self.value > 0:
			self.value = self.value - 2

		embeds = []
		for i in range(self.value, min(self.value + 2, len(self.response))):
			file = self.response[i]
			id = file["id"]
			name = file["name"]
			downloads = human_format(int(file["downloads"]))
			upload_time = int(file["upload_time"])
			utc_time = datetime.datetime.utcfromtimestamp(upload_time)
			readabletime = utc_time.strftime("%Y-%m-%d %H:%M UTC")

			data = subprocess.Popen(
				[
					"curl",
					"https://api.starfiles.co/file/fileinfo/" + id + "?prefetch=true",
				]
			)

			embed = discord.Embed(
				title=f"{name}", color=0x00FF00, timestamp=datetime.datetime.utcnow()
			)
			embed.url = "https://starfiles.co/file/" + id
			embed.set_author(name="Search results")
			embed.add_field(
				name="Downloads: " + str(downloads),
				value=f"Uploaded <t:{upload_time}:R>",
				inline=False,
			)
			embed.set_thumbnail(url=f"https://cdn.starfiles.co/file/icon/{id}")
			embed.set_footer(text=f"Result {i + 1} of {len(self.response)}")
			embeds.append(embed)
		await interaction.edit_original_response(embeds=embeds, view=self)

	def createbackbutton(self):
		return SearchView.BackButton(self)

	class BackButton(discord.ui.Button):
		def __init__(self, outerview):
			self.outer = outerview
			super().__init__(
				label="Back",
				style=discord.ButtonStyle.primary,
			)

		async def callback(self, interaction: discord.Interaction):
			await interaction.response.defer()
			embeds = []
			for i in range(
					self.outer.value, min(self.outer.value + 2, len(self.outer.response))
			):
				file = self.outer.response[i]
				id = file["id"]
				name = file["name"]
				downloads = human_format(int(file["downloads"]))
				upload_time = int(file["upload_time"])
				utc_time = datetime.datetime.utcfromtimestamp(upload_time)
				readabletime = utc_time.strftime("%Y-%m-%d %H:%M UTC")

				data = subprocess.Popen(
					[
						"curl",
						"https://api.starfiles.co/file/fileinfo/"
						+ id
						+ "?prefetch=true",
					]
				)

				embed = discord.Embed(
					title=f"{name}",
					color=0x00FF00,
					timestamp=datetime.datetime.utcnow(),
				)
				embed.url = "https://starfiles.co/file/" + id
				embed.set_author(name="Search results")
				embed.add_field(
					name="Downloads: " + str(downloads),
					value=f"Uploaded <t:{upload_time}:R>",
					inline=False,
				)
				embed.set_thumbnail(url=f"https://cdn.starfiles.co/file/icon/{id}")
				embed.set_footer(text=f"Result {i + 1} of {len(self.outer.response)}")
				embeds.append(embed)
			self.outer.clear_items()
			self.outer.add_item(self.outer.back)
			self.outer.add_item(self.outer.one)
			self.outer.add_item(self.outer.two)
			self.outer.add_item(self.outer.next)
			await interaction.edit_original_response(embeds=embeds, view=self.outer)

	@discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
	async def one(self, button: discord.ui.Button, interaction: discord.Interaction):
		if interaction.user.id != self.owner:
			await interaction.response.send_message(
				"You are not allowed to do this", ephemeral=True
			)
			return

		await interaction.response.defer()

		self.chosen = self.value
		file = self.response[self.value]
		id = file["id"]
		name = file["name"]
		downloads = human_format(int(file["downloads"]))
		upload_time = int(file["upload_time"])
		utc_time = datetime.datetime.utcfromtimestamp(upload_time)
		readabletime = utc_time.strftime("%Y-%m-%d %H:%M UTC")

		data = requests.get(
			"https://api.starfiles.co/file/fileinfo/" + id + "?fetch=true"
		).json()
		try:
			bundleid = data["bundle_id"]

		except KeyError:
			bundleid = ""

		try:
			version = data["version"]
		except KeyError:
			version = ""

		embed = discord.Embed(
			title=f"{name}", color=0x00FF00, timestamp=datetime.datetime.utcnow()
		)
		embed.url = "https://starfiles.co/file/" + id
		embed.set_author(name="Search results")
		embed.add_field(
			name="Downloads: " + str(downloads),
			value=f"Uploaded <t:{upload_time}:R>",
			inline=False,
		)
		if bundleid != None:
			embed.add_field(name=f"Bundle ID: ", value=f"{bundleid}", inline=False)
			embed.add_field(name=f"Version: ", value=f"{version}", inline=False)

		embed.set_thumbnail(url=f"https://cdn.starfiles.co/file/icon/{id}")
		embed.set_footer(text=f"Result {self.value + 1} of {len(self.response)}")
		self.remove_item(self.back)
		self.remove_item(self.next)
		self.remove_item(self.one)
		self.remove_item(self.two)

		self.add_item(
			discord.ui.Button(
				label="Download",
				style=discord.ButtonStyle.blurple,
				url=f"https://download.starfiles.co/{id}",
			))


		if name.endswith(".ipa"):
			self.add_item(
				discord.ui.Button(
					label="Sign",
					style=discord.ButtonStyle.green,
					url=f"https://signtunes.co/signer#{id}",
				)
			)




		self.add_item(self.createbackbutton())
		await interaction.edit_original_response(embed=embed, view=self)

	@discord.ui.button(label="2", style=discord.ButtonStyle.blurple)
	async def two(self, button: discord.ui.Button, interaction: discord.Interaction):
		if interaction.user.id != self.owner:
			await interaction.response.send_message(
				"You are not allowed to do this", ephemeral=True
			)
			return
		await interaction.response.defer()

		self.chosen = self.value + 1
		file = self.response[self.value + 1]
		id = file["id"]
		name = file["name"]
		downloads = human_format(int(file["downloads"]))
		upload_time = int(file["upload_time"])
		utc_time = datetime.datetime.utcfromtimestamp(upload_time)
		readabletime = utc_time.strftime("%Y-%m-%d %H:%M UTC")

		data = requests.get(
			"https://api.starfiles.co/file/fileinfo/" + id + "?fetch=true"
		).json()
		try:
			bundleid = data["bundle_id"]

		except KeyError:
			bundleid = ""

		try:
			version = data["version"]
		except KeyError:
			version = ""

		embed = discord.Embed(
			title=f"{name}", color=0x00FF00, timestamp=datetime.datetime.utcnow()
		)
		embed.url = "https://starfiles.co/file/" + id
		embed.set_author(name="Search results")
		embed.add_field(
			name="Downloads: " + str(downloads),
			value=f"Uploaded <t:{upload_time}:R>",
			inline=False,
		)
		if bundleid != None:
			embed.add_field(name=f"Bundle ID: ", value=f"{bundleid}", inline=False)
			embed.add_field(name=f"Version: ", value=f"{version}", inline=False)

		embed.set_thumbnail(url=f"https://api.starfiles.co/file/icon/{id}")
		embed.set_footer(text=f"Result {self.value + 2} of {len(self.response)}")
		self.remove_item(self.back)
		self.remove_item(self.next)
		self.remove_item(self.one)
		self.remove_item(self.two)

		self.add_item(
			discord.ui.Button(
				label="Download",
				style=discord.ButtonStyle.blurple,
				url=f"https://download.starfiles.co/{id}",
			))


		if name.endswith(".ipa"):
			self.add_item(
				discord.ui.Button(
					label="Sign",
					style=discord.ButtonStyle.green,
					url=f"https://signtunes.co/signer#{id}",
				)
			)



		self.add_item(self.createbackbutton())
		await interaction.edit_original_response(embed=embed, view=self)

	@discord.ui.button(label="Next", style=discord.ButtonStyle.green)
	async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
		if interaction.user.id != self.owner:
			await interaction.response.send_message(
				"You are not allowed to do this", ephemeral=True
			)
			return
		await interaction.response.defer()
		if self.value < len(self.response) - 2:
			self.value = self.value + 2

		embeds = []
		for i in range(self.value, min(self.value + 2, len(self.response))):
			file = self.response[i]
			id = file["id"]
			name = file["name"]
			downloads = human_format(int(file["downloads"]))
			upload_time = int(file["upload_time"])
			utc_time = datetime.datetime.utcfromtimestamp(upload_time)
			readabletime = utc_time.strftime("%Y-%m-%d %H:%M UTC")
			data = subprocess.Popen(
				[
					"curl",
					"https://api.starfiles.co/file/fileinfo/" + id + "?prefetch=true",
				]
			)

			embed = discord.Embed(
				title=f"{name}", color=0x00FF00, timestamp=datetime.datetime.utcnow()
			)
			embed.url = "https://starfiles.co/file/" + id
			embed.set_author(name="Search results")
			embed.add_field(
				name="Downloads: " + str(downloads),
				value=f"Uploaded <t:{upload_time}:R>",
				inline=False,
			)
			embed.set_thumbnail(url=f"https://cdn.starfiles.co/file/icon/{id}")
			embed.set_footer(text=f"Result {i + 1} of {len(self.response)}")
			embeds.append(embed)
		await interaction.edit_original_response(embeds=embeds, view=self)


@option("search", description="file name to search for", required=True)
@bot.slash_command()
async def search(ctx, search: str):
	payload = {
		"public": "true",
		"group": "hash",
		"collapse": "true",
		"search": search,
		"sort": "trending",
	}
	url = f"https://api2.starfiles.co/files"
	headers = {"User-Agent": "SignTunes discord bot"}
	response = requests.get(url, headers=headers, params=payload)
	embeds = []
	if response.ok:
		if len(response.json()) < 1:
			await ctx.interaction.followup.send("No results found")
			return

		view = SearchView()
		view.get_response(response.json(), ctx.author.id)
		for i in range(0, min(2, len(response.json()))):
			file = response.json()[i]
			id = file["id"]
			name = file["name"]
			downloads = human_format(int(file["downloads"]))
			upload_time = int(file["upload_time"])
			utc_time = datetime.datetime.utcfromtimestamp(upload_time)
			readabletime = utc_time.strftime("%Y-%m-%d %H:%M UTC")
			data = subprocess.Popen(
				[
					"curl",
					"https://api.starfiles.co/file/fileinfo/" + id + "?prefetch=true",
				]
			)
			embed = discord.Embed(
				title=f"{name}", color=0x00FF00, timestamp=datetime.datetime.utcnow()
			)
			embed.url = "https://starfiles.co/file/" + id
			embed.set_author(name="Search results")
			embed.add_field(
				name="Downloads: " + str(downloads),
				value=f"Uploaded <t:{upload_time}:R>",
				inline=False,
			)
			embed.set_thumbnail(url=f"https://cdn.starfiles.co/file/icon/{id}")
			embed.set_footer(text=f"Result {i + 1} of {len(response.json())}")
			embeds.append(embed)
		await ctx.respond(embeds=embeds, view=view)
		await view.wait()
	else:
		await ctx.respond("Failed to search for file, error: " + response.text)
		return


@bot.slash_command()
async def get_udid(ctx: discord.ApplicationContext):
	await ctx.respond(
		"To get your UDID, visit https://udid.starfiles.co/ from your apple device"
	)


def parse_starfile_url(url):
	if url.startswith("https://starfiles.co/file/"):
		data = url.split("/")
		bid = data[4]
	elif url.startswith("https://sts.st/"):
		data = url.split("/")
		bid = data[4]
	elif url.startswith("https://api.starfiles.co/direct/"):
		data = url.split("/")
		bid = data[4]
	elif not url.startswith("http"):
		bid = url  # in this case, it's probably not an URL anyway
	return bid




class AppSearchView(discord.ui.View):
	def __init__(self):
		super().__init__()
		self.value = 0

	def get_response(self, response, triggerer):
		self.response = response
		self.owner = triggerer

	def createbutton1(self):
		return AppSearchView.BundleID1(self)

	class BundleID1(discord.ui.Button):
		def __init__(self, outerview):
			self.outer = outerview
			super().__init__(
				label="Bundle ID 1",
				style=discord.ButtonStyle.primary,
				row=1
			)

		async def callback(self, interaction: discord.Interaction):
			if interaction.user.id != self.outer.owner:
				await interaction.response.send_message(
					"You are not allowed to do this", ephemeral=True
				)
				return
			await interaction.response.send_message(content=f"{self.outer.response[self.outer.value]['bundleId']}",
													view=None)

	def createbutton2(self):
		return AppSearchView.BundleID2(self)

	class BundleID2(discord.ui.Button):
		def __init__(self, outerview):
			self.outer = outerview
			super().__init__(
				label="Bundle ID 2",
				style=discord.ButtonStyle.primary,
				row=1
			)

		async def callback(self, interaction: discord.Interaction):
			if interaction.user.id != self.outer.owner:
				await interaction.response.send_message(
					"You are not allowed to do this", ephemeral=True
				)
				return
			await interaction.response.send_message(content=f"{self.outer.response[self.outer.value + 1]['bundleId']}",
													view=None)

	@discord.ui.button(label="Back", style=discord.ButtonStyle.green)
	async def back(self, button: discord.ui.Button, interaction: discord.Interaction):
		if interaction.user.id != self.owner:
			await interaction.response.send_message(
				"You are not allowed to do this", ephemeral=True
			)
			return

		if self.value > 0:
			self.value = self.value - 2

		embeds = []
		for i in range(self.value, min(self.value + 2, len(self.response))):
			file = self.response[i]
			embed = discord.Embed(
				title=file["trackCensoredName"],
				color=0x00FF00,
				timestamp=datetime.datetime.utcnow(),
			)
			embed.url = file["trackViewUrl"]
			embed.set_thumbnail(url=file["artworkUrl100"])
			try:
				embed.add_field(name="Price", value=file["formattedPrice"], inline=True)
			except KeyError:
				embed.add_field(name="Price", value="Free", inline=True)
			embed.add_field(
				name="Rating", value=str(file["averageUserRating"]), inline=True
			)
			embed.add_field(name="Bundle ID", value=file["bundleId"], inline=False)
			embeds.append(embed)

		self.clear_items()
		self.add_item(self.back)
		self.add_item(self.next)
		self.add_item(self.createbutton1())
		self.add_item(self.createbutton2())
		await interaction.response.edit_message(embeds=embeds, view=self)

	@discord.ui.button(label="Next", style=discord.ButtonStyle.green)
	async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
		if interaction.user.id != self.owner:
			await interaction.response.send_message(
				"You are not allowed to do this", ephemeral=True
			)
			return

		if self.value < len(self.response) - 2:
			self.value = self.value + 2

		embeds = []
		for i in range(self.value, min(self.value + 2, len(self.response))):
			file = self.response[i]
			embed = discord.Embed(
				title=file["trackCensoredName"],
				color=0x00FF00,
				timestamp=datetime.datetime.utcnow(),
			)
			embed.url = file["trackViewUrl"]
			embed.set_thumbnail(url=file["artworkUrl100"])
			try:
				embed.add_field(name="Price", value=file["formattedPrice"], inline=True)
			except KeyError:
				embed.add_field(name="Price", value="Free", inline=True)
			embed.add_field(
				name="Rating", value=str(file["averageUserRating"]), inline=True
			)
			embed.add_field(name="Bundle ID", value=file["bundleId"], inline=False)
			embeds.append(embed)
		self.clear_items()
		self.add_item(self.back)
		self.add_item(self.next)
		self.add_item(self.createbutton1())
		self.add_item(self.createbutton2())
		await interaction.response.edit_message(embeds=embeds, view=self)

@option("bundleid", description="Enter the bundle ID of the app to decrypt")
@bot.slash_command()
async def decrypt(ctx, bundleid: str):
	await ctx.defer()
	url1 = f"https://api2.starfiles.co/appstore_lookup?bundleId={bundleid}"

	response = requests.get(url1)
	data = response.json()
	if data["resultCount"] < 1:
		await ctx.interaction.followup.send("No apps found")
		return


	file = data["results"][0]
	id = file["trackId"]
	url2 = f"https://api2.starfiles.co/request_ipa/{id}"
	response = requests.get(url2).json()

	if response["success"] == False:
		if response["errors"][0]["code"] == "ERROR_SUCH_VERSION_EXISTS_AND_LINKS_AVAILABLE":

			embed = discord.Embed(title="File already decrypted", color=0x008000, timestamp=datetime.datetime.utcnow())
			embed.add_field(name="App Name", value=file["trackCensoredName"], inline=False)
			try:
				embed.add_field(name="Price", value=file["formattedPrice"], inline=True)
			except KeyError:
				embed.add_field(name="Price", value="Free", inline=True)
			embed.add_field(
				name="Rating", value=str(file["averageUserRating"]), inline=True
			)
			embed.add_field(name="Bundle ID", value=file["bundleId"], inline=False)
			embed.set_thumbnail(url=file["artworkUrl100"])
			embed.url = f"https://starfiles.co/bundle_id/{file['bundleId']}"
			await ctx.interaction.followup.send(embed=embed)
			return

		if response["errors"][0]["code"] == "ERROR_NO_SUCH_APP_IN_APPSTORE_LOCAL":
			await ctx.interaction.followup.send(f"Error occured: {response['errors'][0]['translated']}")
	else:
		embed = discord.Embed(title="File Decryption Requested", color=0x00FF00, timestamp=datetime.datetime.utcnow())
		embed.add_field(name="App Name", value=file["trackCensoredName"], inline=False)
		try:
			embed.add_field(name="Price", value=file["formattedPrice"], inline=True)
		except KeyError:
			embed.add_field(name="Price", value="Free", inline=True)

		embed.add_field(name="Rating", value=str(file["averageUserRating"]), inline=True)
		embed.add_field(name="Bundle ID", value=file["bundleId"], inline=False)
		embed.set_thumbnail(url=file["artworkUrl100"])
		embed.set_footer(text=f"The application will be on starfiles shortly")
		await ctx.interaction.followup.send(embed=embed)

		while True:
			await asyncio.sleep(300)
			url3 = f"https://api2.starfiles.co/request_ipa/{id}"
			response = requests.get(url3).json()
			if response["success"] == True:
				continue
			else:
				if response["errors"][0]["code"] == "ERROR_SUCH_VERSION_EXISTS_AND_LINKS_AVAILABLE":
					embed = discord.Embed(title="Your app has been decrypted!", color=0x008000, timestamp=datetime.datetime.utcnow())
					embed.add_field(name="App Name", value=file["trackCensoredName"], inline=False)
					try:
						embed.add_field(name="Price", value=file["formattedPrice"], inline=True)
					except KeyError:
						embed.add_field(name="Price", value="Free", inline=True)
					embed.add_field(
						name="Rating", value=str(file["averageUserRating"]), inline=True
					)
					embed.add_field(name="Bundle ID", value=file["bundleId"], inline=False)
					embed.set_thumbnail(url=file["artworkUrl100"])
					embed.url = f"https://starfiles.co/bundle_id/{file['bundleId']}"
					await ctx.interaction.message.reply(embed=embed)


def insert_returns(body):
	# insert return stmt if the last expression is a expression statement
	if isinstance(body[-1], ast.Expr):
		body[-1] = ast.Return(body[-1].value)
		ast.fix_missing_locations(body[-1])

	# for if statements, we insert returns into the body and the orelse
	if isinstance(body[-1], ast.If):
		insert_returns(body[-1].body)
		insert_returns(body[-1].orelse)

	# for with blocks, again we insert returns into the body
	if isinstance(body[-1], ast.With):
		insert_returns(body[-1].body)


class EvalModal(discord.ui.Modal):
	def __init__(self, message, bot, discord, commands, ctx, *args, **kwargs) -> None:
		self.message = message
		self.bot = bot
		self.discord = discord
		self.commands = commands
		self.ctx = ctx

		super().__init__(
			discord.ui.InputText(
				style=discord.InputTextStyle.long,
				label="Code to eval",
				placeholder="Enter code to eval"),
			*args, **kwargs)

	async def callback(self, interaction: discord.Interaction):
		await interaction.response.defer()
		response = await eval_fn(self.message, cmd=self.children[0].value, botobject=self.bot, discordobj=self.discord,
								 commandsobj=self.commands, ctxobj=self.ctx)
		response = str(response)
		textpages = []
		for page in wrap(response, 1950, replace_whitespace=False, drop_whitespace=False, break_long_words=False):
			textpages.append(page)

		paginator = pages.Paginator(pages=textpages)

		await paginator.respond(interaction)


async def eval_fn(ctx, cmd, botobject, discordobj, commandsobj, ctxobj):
	fn_name = "_eval_expr"
	try:
		cmd = cmd.strip("` ")

		# add a layer of indentation
		cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

		# wrap in async def body
		body = f"async def {fn_name}():\n{cmd}"
		parsed = ast.parse(body)
		body = parsed.body[0].body
		insert_returns(body)
		env = {
			'bot': botobject,
			'discord': discordobj,
			'commands': commandsobj,
			'ctx': ctxobj,
			'__import__': __import__
		}
		exec(compile(parsed, filename="<ast>", mode="exec"), env)
		result = (await eval(f"{fn_name}()", env))
	except:
		result = traceback.format_exc()

	# convert result from binary to string
	if isinstance(result, bytes):
		result = result.decode("utf-8")

	return result


@bot.slash_command()
async def runcode(ctx: discord.ApplicationContext):
	if ctx.author.id not in [419742289188093952, 366829983294816258]:
		await ctx.respond("You are not allowed to use this command.")
		return

	modal = EvalModal(title="Run Code Modal", message=ctx.message, bot=bot, discord=discord, commands=commands, ctx=ctx)
	await ctx.send_modal(modal)



@option("name", description="Enter the name of the app to search for")
@bot.slash_command()
async def searchappstore(ctx, name: str):
	await ctx.defer()
	options = {"media": "software", "term": name}
	url = "https://api2.starfiles.co/appstore_search"

	response = requests.get(url, params=options)
	data = response.json()
	if data["resultCount"] < 1:
		await ctx.respond("No apps found")
		return
	embeds = []
	for i in range(0, min(2, len(data["results"]))):
		file = data["results"][i]
		embed = discord.Embed(
			title=file["trackCensoredName"],
			color=0x00FF00,
			timestamp=datetime.datetime.utcnow(),
		)
		embed.url = f"https://starfiles.co/bundle_id/{file['bundleId']}"
		embed.set_thumbnail(url=file["artworkUrl100"])
		try:
			embed.add_field(name="Price", value=file["formattedPrice"], inline=True)
		except KeyError:
			embed.add_field(name="Price", value="Free", inline=True)
		embed.add_field(
			name="Rating", value=str(file["averageUserRating"]), inline=True
		)
		embed.add_field(name="Bundle ID", value=file["bundleId"], inline=False)
		embeds.append(embed)
	view = AppSearchView()
	view.response = data["results"]
	view.owner = ctx.author.id
	view.add_item(view.createbutton1())
	view.add_item(view.createbutton2())
	await ctx.interaction.followup.send(embeds=embeds, view=view)


@bot.slash_command()
async def synccommand(ctx):
	await bot.sync_commands(force=True)
	await ctx.respond("Commands synced")

bot.run(token)
