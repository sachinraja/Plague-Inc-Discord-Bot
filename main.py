import discord
from discord.ext import commands
import logging
import jsonpickle
from random import randrange, randint
import keep_alive
from PIL import Image
from io import BytesIO
from os import getenv
from dotenv import load_dotenv

# load environment variables
load_dotenv()
BOT_TOKEN = getenv('TOKEN')

# logging
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

bot = commands.Bot(command_prefix='p!')
bot.remove_command('help')

class Spot():

    def __init__(self, spot_type, continent, population):
        self.spot_type = spot_type
        
        if spot_type == 'water':
            self.color = (0, 0, 255)

        elif spot_type == 'land':
            self.color = (0, 255, 0)

        elif spot_type == 'infected':
            self.color = (255, 0, 0)
        
        self.continent = continent
        self.population = population

class Map():
    
    def __init__(self, width, height, spot_list):
        self.width = width
        self.height = height
        self.spot_list = spot_list

    def map_to_image(self):
        map_image = Image.new('RGB', (self.width, self.height), color = 'red')

        i = 0
        for y in range(self.height):
          for x in range(self.width):
                map_image.putpixel((x, y), self.spot_list[i].color)
                i += 1

        # upscale image
        map_image = map_image.resize((self.width * 10, self.height * 10), resample=Image.NEAREST)

        # switch to bytes
        with BytesIO() as image_binary:
            map_image.save(image_binary, 'PNG')
            image_binary.seek(0)
            im_map = discord.File(fp=image_binary, filename='image.png')
            return im_map
    
    def get_population(self):
        population = 0
        infected_population = 0
        for spot in self.spot_list:
            population += spot.population

            if spot.spot_type == 'infected':
                infected_population += spot.population
        
        return(population, infected_population)

    def get_embed(self, author_name):
        population = self.get_population()

        embed_map = discord.Embed(title='Map', color=255)\
        .add_field(name='Population', value=str(population[0]), inline=False)\
        .add_field(name='Infected Population', value=str(population[1]), inline=False)\
        .set_image(url='attachment://image.png')\
        .set_author(name=author_name)

        return embed_map

class Upgrade():
    
    def __init__(self, name, max_level, level, base_cost, interval):
        self.name = name
        self.max_level = max_level
        self.level = level
        self.base_cost = base_cost
        self.interval = interval

    def add_level(self):
        self.level += self.interval
    
    def __str__(self):
        return f'{self.name} is level {self.level}.'

class Game():

    def __init__(self, map, points, upgrades, cure_percent):
        self.map = map
        self.points = points
        self.upgrades = upgrades
        self.cure_percent = cure_percent

    def save(self, user_id):
        with open('Player_Games/' + user_id + '.json', 'w') as f:
            f.write(jsonpickle.encode(self))

def load_game(user_id):
    try:
        with open('Player_Games/' + user_id + '.json', 'r') as f:
            player_game = jsonpickle.decode(f.read())
            return player_game
    
    except:
        return 0
            
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command(name='help')
async def help_message(ctx):
    '''
    Shows the list of commands and what they do.
    '''

    embed_help_message = discord.Embed(title='Help', color=65280)\
    .add_field(name="p!newgame [map_name]", value = "Starts a new game on map_name.", inline=False)\
    .add_field(name="p!map", value = "Shows your current game's map.", inline=False)\
    .add_field(name="p!place [continent]", value = "Begins the spread of the infection by placing an infected tile somewhere in continent.", inline=False)\
    .add_field(name="p!next", value = "Goes to the next day, which spreads the infection and updates the cure percentage.", inline=False)\
    .add_field(name="p!upgrade [upgrade]", value = "Upgrades upgrade to the next level.", inline=False)\
    .add_field(name="p!upgrades", value = "Shows a list of your current game's upgrades and their levels.", inline=False)

    await ctx.send(embed=embed_help_message)

@bot.command(name='newgame', rest_is_raw=True)
async def new_game(ctx, *, map_name):
    '''
    Create new game
    '''
    
    if map_name == '':
        await ctx.send('Enter a valid map name after p!newgame. Ex: p!newgame map1.')
        return

    map_name = map_name[1:]
    
    try:
        player_map = 0
        with open('Maps/' + map_name.lower() + '.json', 'r') as f:
            player_map = jsonpickle.decode(f.read())
    
    except:
        await ctx.send('Enter a valid map name after p!newgame. Ex: p!newgame map1.')
        return

    upgrades = [Upgrade('air transmission', 3, 0, 9, 1), Upgrade('water transmission', 2, 0, 9, 1), Upgrade('livestock transmission', 3, 0, 7, 1),
    Upgrade('pest transmission', 2, 0, 10, 1), Upgrade('blood transmission', 2, 0, 8, 1)]

    player_game = Game(player_map, 1000, upgrades, 0)
    player_game.save(str(ctx.author.id))

    await ctx.send(file=player_map.map_to_image(), embed=player_map.get_embed(ctx.author.name))

@bot.command(name='map')
async def display_map(ctx):
    '''
    Displays the map of the game.
    '''

    player_game = load_game(str(ctx.author.id))

    if (player_game == 0):
        await ctx.send('No game found! Create a game with p!newgame.')
        return

    player_map = player_game.map

    await ctx.send(file=player_map.map_to_image(), embed=player_map.get_embed(ctx.author.name))

@bot.command(name='place', rest_is_raw=True)
async def place_infected(ctx, *, continent):
    '''
    Infects a random place on the continent chosen.
    '''

    player_game = load_game(str(ctx.author.id))

    if (player_game == 0):
        await ctx.send('No game found! Create a game with p!newgame.')
        return

    player_map = player_game.map

    # check if an actual continent was entered
    if continent == '':
        await ctx.send('Enter a valid continent after p!place. Ex: p!place North America.')
        return
    
    continent = continent[1:]

    # check if player has already placed
    for check_type_spot in player_map.spot_list:
        if check_type_spot.spot_type == 'infected':
            await ctx.send('You have already started your disease.')
            return

    # get continent they want to place on and place it randomly on a spot there
    valid_placements = []

    for check_continent_spot in player_map.spot_list:
        if check_continent_spot.spot_type != 'water':
            if continent.lower() == check_continent_spot.continent.lower():
                valid_placements.append(check_continent_spot)
    
    # check if the continent has any tiles to infect
    if len(valid_placements) == 0:
        await ctx.send('Enter a valid continent after p!place. Ex: p!place North America.')
        return

    # choose one spot out of the spots on the list
    random_placement = randrange(0, len(valid_placements))
    valid_placements[random_placement].spot_type = 'infected'
    valid_placements[random_placement].color = (255, 0, 0)

    await ctx.send(file=player_map.map_to_image(), embed=player_map.get_embed(ctx.author.name))

    player_game.save(str(ctx.author.id))

@bot.command(name='next')
async def next_day(ctx):
    '''
    Spreads infection, goes to "next day".
    '''

    player_game = load_game(str(ctx.author.id))

    if (player_game == 0):
        await ctx.send('No game found! Create a game with p!newgame.')
        return

    player_map = player_game.map

    # save new infections as set and then iterate over it to change attributes
    new_infections = set()
    i = 0
    infect_chance = player_game.upgrades[0].level + player_game.upgrades[1].level + player_game.upgrades[2].level\
        + player_game.upgrades[3].level + player_game.upgrades[4].level

    for spot in player_map.spot_list:
        if spot.spot_type == 'infected':
            if randint(infect_chance, 15) == 15:
                if player_map.spot_list[i - 1].spot_type == 'land':
                    new_infections.add(player_map.spot_list[i - 1])
            
            try:
                if randint(infect_chance, 15) == 15:
                    if player_map.spot_list[i + 1].spot_type == 'land':
                        new_infections.add(player_map.spot_list[i + 1])
                
            except IndexError:
                index = i + 1
                index = (index - player_map.width) * -1
                if player_map.spot_list[index].spot_type == 'land':
                    new_infections.add(player_map.spot_list[index])

            if randint(infect_chance, 15) == 15:
                if player_map.spot_list[i - player_map.width].spot_type == 'land':
                    new_infections.add(player_map.spot_list[i - player_map.width])

            try:
                if randint(infect_chance, 15) == 15:
                    if player_map.spot_list[i + player_map.width].spot_type == 'land':
                        new_infections.add(player_map.spot_list[i + player_map.width])
            
            except IndexError:
                index = i * -1
                if player_map.spot_list[index].spot_type == 'land':
                    new_infections.add(player_map.spot_list[index])
        
        i += 1

    for infection in new_infections:
            infection.spot_type = 'infected'
            infection.color = (255, 0, 0)

    population = player_map.get_population()

    embed_map = discord.Embed(title='Map', color=255)\
    .add_field(name='Population', value=str(population[0]), inline=False)\
    .add_field(name='Infected Population', value=str(population[1]))\
    .add_field(name='New Infections', value=len(new_infections))\
    .set_image(url='attachment://image.png')\
    .set_author(name=ctx.author.name)

    await ctx.send(file=player_map.map_to_image(), embed=embed_map)

    player_game.save(str(ctx.author.id))

@bot.command(name='upgrade', rest_is_raw=True)
async def upgrade(ctx, *, upgrade_arg):
    '''
    Upgrade virus attributes.
    '''

    player_game = load_game(str(ctx.author.id))

    if (player_game == 0):
        await ctx.send('No game found! Create a game with p!newgame.')
        return
        
    if upgrade_arg == '':
        await ctx.send('Enter a valid upgrade after p!upgrade. Ex: p!upgrade Infect Speed.')
        return

    upgrade_text = upgrade_arg[1:]
    upgrade_arg = upgrade_arg[1:].lower()
    
    upgrade = 0
    for player_upgrade in player_game.upgrades:
        if upgrade_arg == player_upgrade.name:
            upgrade = player_upgrade
            break
    
    if upgrade == 0:
        await ctx.send('Enter a valid upgrade after p!upgrade. Ex: p!upgrade Infect Speed.')
        return

    if upgrade.level < upgrade.max_level:
        points_required = upgrade.base_cost + (upgrade.level * upgrade.interval)

        if player_game.points >= points_required:
            upgrade.level += 1
            player_game.points -= points_required
        
        else:
            await ctx.send(f'You only have {str(player_game.points)} point(s), you need {str(points_required)} points to upgrade {upgrade_text}.')
            return
    
    else:
        await ctx.send(f'{upgrade_text} is already at max level - level {str(upgrade.level)}.')
        return

    await ctx.send(f'{upgrade_text} is now level {str(upgrade.level)}.')

    player_game.save(str(ctx.author.id))

@bot.command(name='upgrades')
async def upgrades_list(ctx):
    '''
    Show list of upgrades and their current level to player.
    '''

    player_game = load_game(str(ctx.author.id))

    if (player_game == 0):
        await ctx.send('No game found! Create a game with p!newgame.')
        return

    embed_upgrades_list = discord.Embed(title='Upgrades', color=16711680)\
    .add_field(name='Points', value=str(player_game.points))
    for upgrade in player_game.upgrades:
        upgrade_message = f'Level {upgrade.level} / {upgrade.max_level}'
        embed_upgrades_list = embed_upgrades_list.add_field(name=upgrade.name, value =upgrade_message, inline=False)
    
    await ctx.send(embed=embed_upgrades_list)

keep_alive.keep_alive()

bot.run(BOT_TOKEN)