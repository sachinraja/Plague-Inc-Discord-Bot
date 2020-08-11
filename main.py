import discord
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

client = discord.Client()

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

    def save_map(self, user_id):
        with open('Player_Maps/' + user_id + '.json', 'w') as f:
            f.write(jsonpickle.encode(self))
    
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

        embed_map = discord.Embed(title='Map')\
        .add_field(name='Population', value=str(population[0]), inline=False)\
        .add_field(name='Infected Population', value=str(population[1]), inline=False)\
        .set_image(url='attachment://image.png')\
        .set_author(name=author_name)

        return embed_map

def load_map(user_id):
    try:
        with open('Player_Maps/' + user_id + '.json', 'r') as f:
            player_map = jsonpickle.decode(f.read())
            return player_map
    
    except:
        return 0

class Game():

    def __init__(self, map):
        pass

@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Create new game
    if message.content.startswith('p$newgame'):

        player_map = 0
        with open('Maps/map1.json', 'r') as f:
            player_map = jsonpickle.decode(f.read())

        await message.channel.send(file=player_map.map_to_image(), embed=player_map.get_embed(message.author.name))

        player_map.save_map(str(message.author.id))
        
    
    elif message.content.startswith('p$'):

        player_map = load_map(str(message.author.id))

        if (player_map == 0):
            await message.channel.send('No game found! Create a game with p$newgame.')
            return

        if message.content.startswith('p$map'):
            await message.channel.send(file=player_map.map_to_image(), embed=player_map.get_embed(message.author.name))

        elif message.content.startswith('p$place'):
            # check if player has already placed
            for check_type_spot in player_map.spot_list:
                if check_type_spot.spot_type == 'infected':
                    await message.channel.send('You have already started your disease.')
                    return

            # get continent they want to place on and place it randomly on a spot there
            continent = message.content[8:]
            valid_placements = []

            for check_continent_spot in player_map.spot_list:
                if check_continent_spot.spot_type != 'water':
                    if continent.lower() == check_continent_spot.continent.lower():
                        valid_placements.append(check_continent_spot)
            
            if len(valid_placements) == 0:
                if continent == '':
                    await message.channel.send(f'Enter a valid continent after p$place. Ex: p$place North America.')
                    return

                await message.channel.send(f'{continent} is not a valid continent.')
                return

            # choose one spot out of the spots on the list
            random_placement = randrange(0, len(valid_placements))
            valid_placements[random_placement].spot_type = 'infected'
            valid_placements[random_placement].color = (255, 0, 0)

            await message.channel.send(file=player_map.map_to_image(), embed=player_map.get_embed(message.author.name))

            player_map.save_map(str(message.author.id))

        elif message.content.startswith('p$next'):
            
            # save new infections as set and then iterate over it to change attributes
            new_infections = set()
            i = 0
            for spot in player_map.spot_list:
                if spot.spot_type == 'infected':
                    if randint(0, 3) == 0:
                        if player_map.spot_list[i - 1].spot_type == 'land':
                            new_infections.add(player_map.spot_list[i - 1])
                    
                    try:
                        if randint(0, 3) == 0:
                            if player_map.spot_list[i + 1].spot_type == 'land':
                                new_infections.add(player_map.spot_list[i + 1])
                        
                    except IndexError:
                        index = i + 1
                        index = (index - player_map.width) * -1
                        if player_map.spot_list[index].spot_type == 'land':
                            new_infections.add(player_map.spot_list[index])

                    if randint(0, 3) == 0:
                        if player_map.spot_list[i - player_map.width].spot_type == 'land':
                            new_infections.add(player_map.spot_list[i - player_map.width])

                    try:
                        if randint(0, 3) == 0:
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

            embed_map = discord.Embed(title='Map')\
            .add_field(name='Population', value=str(population[0]), inline=False)\
            .add_field(name='Infected Population', value=str(population[1]))\
            .add_field(name='New Infections', value=len(new_infections))\
            .set_image(url='attachment://image.png')\
            .set_author(name=message.author.name)

            await message.channel.send(file=player_map.map_to_image(), embed=embed_map)

            player_map.save_map(str(message.author.id))

keep_alive.keep_alive()

client.run(BOT_TOKEN)