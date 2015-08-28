documentation="""
Definitely Not Galcon, Copyright 2014-2015 Jasper Chapman-Black
Controls:
  left-click to select a friendy planet, or drag to select several
  right-click a planet to attack with fleets from selected planets
  space to pause


Command Line Arguments:
  -help		useful information on command line arguments
  -fps x	sets max fps to x (x>0)
  -ai		sets game mode to a match between two AIs
  -aitempo x	alters ai rate. as x approaches 1, ai reacts faster
  -pacifist		enemies don't do anything
  -shipspeed x	sets maximum ship speed, in px/s. default is 50
  -maxships x	sets soft cap on number of ships displayed
  -blindmode	hides enemy power levels because the game isn't hard enough
  -size w h		sets screen width, height
Suggested Useful Game Modes:
  
  -aitempo 1 -ai -shipspeed 250 -maxships 1000"""

import sys
import pygame, math, random
from pygame import gfxdraw

#VARIOUS CONSTANTS
REPULSION_DISTANCE=25
REPULSION_CONSTANT=2500000. #basically -G
MAXSPEED=50		#pixels per second
MAXACCEL=10000		#maximum ship acceleration
SHIPACCEL=500

RESTORATIVE_CONSTANT=2600

PLANETARY_TOLERANCE=20
PLANETARY_REPULSION_CONSTANT=50000
PLANETARY_REPULSION_BASE=1.15

MAX_NUMBER_OF_SHIPS=150		#maximum number of ships displayed on the screen at one time

AI_TEMPO=1
BLINDMODE=False

def normalize(a,b):
	if a<b:
		return a
	return b

def distance((x0,y0),(x1,y1)):
	return math.sqrt(((x1-x0)**2) + ((y1-y0)**2))

def floorint(n):
	return int(math.floor(n))

def choosefromdistribution(distro):
	n=sum([i[0] for i in distro])
	r=random.uniform(0,n)
	i=-1
	while r>0:
		i+=1
		r-=distro[i][0]
	return distro[i]

def pointInRectangle((x,y),(A,B),(C,D)):
	if A>C: A,C=C,A
	if B>D: B,D=D,B
	return A<x and x<C and B<y and y<D

def intersectCircle((cx,cy),r,(x1,y1),(x2,y2)):
	t=-3	#tolerance
	if x1==x2:
		return y2>cy-r-t and y1<cy+r+t and x1<cx+r+t and cx-r-t<x2
	elif y1==y2:
		return x2>cx-r-t and x1<cx+r+t and y1<cy+r+t and cy-r-t<y2
	
	else:
		print "Error: IntersectCircle passed line not perpendicular to axes"
		raise Exception

def intersect((cx,cy),r,(A, B),(C, D)):
	if A>C: A,C=C,A
	if B>D: B,D=D,B
	return pointInRectangle((cx,cy),(A,B),(C,D)) or \
		intersectCircle((cx,cy),r,(A,B),(C,B)) or \
		intersectCircle((cx,cy),r,(A,D),(C,D)) or \
		intersectCircle((cx,cy),r,(A,B),(A,D)) or \
		intersectCircle((cx,cy),r,(C,B),(C,D))


def TestingSuite():
	print "Testing distance():",
	assert distance((0,0),(0,0))==0
	assert distance((0,0),(1,1))==math.sqrt(2)
	print "passed"

class Planet(object):
	def __init__(self,(x,y),radius,growth,power,team):
		global totalpower
		if team!=0:
			totalpower+=power
		
		self.x,self.y=(x,y)
		self.radius=radius
		self.growth=growth
		self.power=power
		self.team=team
	
	def addPower(self,dP):
		self.power+=dP
	
	def update(self,dt):
		global totalpower
		if self.team!=0:
			self.power+=self.growth*dt
			totalpower+=self.growth*dt

	def drawborder(self,screen,color):
		gfxdraw.aacircle(screen,self.x,self.y,self.radius,color)
		gfxdraw.filled_circle(screen,self.x,self.y,self.radius,color)
	
	def drawfill(self,screen,color):
		gfxdraw.aacircle(screen,self.x,self.y,self.radius-4,color)
		gfxdraw.filled_circle(screen,self.x,self.y,self.radius-4,color)
		
	def drawpower(self,screen):
		global myfont
		label = myfont.render(str(floorint(self.power)), 1, (255,255,0))
		screen.blit(label, (self.x-(label.get_width()/2),self.y-(label.get_height()/2)))
	
	def draw(self,screen):
		self.drawborder(screen,planetbordercolors[self.team])
		self.drawfill(screen,planetfillcolors[self.team])
		
class Boid(object):
	"""Generic class for ships. Technically not boids, more like boid-likes."""
	#graphic=((-1,-1),(1,-1),(0,2))
	graphic=((-5,-5),(5,-5),(0,10))
	a=math.pi/2
	graphic=[(i[0]*math.cos(a)-i[1]*math.sin(a) , i[0]*math.sin(a)+i[1]*math.cos(a)) for i in graphic]

	offset=(-0.1,0.1)

	def __init__(self,start,end,power,team):
		"""start, end are Planet objects
		power is the size of the fleet"""
		self.end=end
		self.power=power
		self.team=team
		
		self.x=start.x
		self.y=start.y
		self.vx=(end.x-start.x)
		self.vy=(end.y-start.y)
		self.ax=0
		self.ay=0

		self.normalizeVelocity()
		
		self.x+=self.vx*start.radius*0.003
		self.y+=self.vy*start.radius*0.003
		
		self.angle=math.atan2(-self.vy,self.vx)
		self.updateAngle()

	def normalizeAcceleration(self):
		"""Normalizes acceleration such that vx^2 + vy^2 < MAXACCEL^2"""
		if self.ax or self.ay:
			factor=(MAXACCEL/math.sqrt(self.ax**2 + self.ay**2))
			if factor<1:
				self.ax*=factor
				self.ay*=factor

	def normalizeVelocity(self):
		"""Normalizes velocity such that vx^2 + vy^2 < MAXSPEED^2"""
		factor=(MAXSPEED/math.sqrt(self.vx**2 + self.vy**2))
		if factor<1:
			self.vx*=factor
			self.vy*=factor
	
	def updateAngle(self):
		#gradual_factor=10
		
		self.angle=math.atan2(-self.vy,-self.vx)
		#else:
		#	self.angle=((gradual_factor*self.angle)+math.atan(self.vy/self.vx))/(gradual_factor+1)
		
		self.graphic=[(i[0]*math.cos(self.angle)-i[1]*math.sin(self.angle) , i[0]*math.sin(self.angle)+i[1]*math.cos(self.angle)) for i in Boid.graphic]

	def update(self,dt):
		"""Updates position, then returns -1 if due for deletion, and 0 if not."""
		self.normalizeVelocity()

		self.x+=self.vx*dt
		self.y+=self.vy*dt
		
		self.x+=random.choice(Boid.offset)
		self.y+=random.choice(Boid.offset)

		#check if target planet has been reached
		if distance((self.x,self.y),(self.end.x,self.end.y))<self.end.radius:	#if you're close to your target
			if self.team==self.end.team:
				self.end.power+=self.power
			else:
				if self.power>self.end.power:
					global totalpower
					totalpower-=(2*self.power)
					
					self.end.power=self.power-self.end.power
					self.end.team=self.team
				else:
					self.end.power-=self.power
					totalpower-=2*self.power
			return -1

		self.updateAngle()
		return 0
	
	
	def draw(self,screen):
		#gfxdraw.pixel(screen, self.x, self.y, planetfillcolors[self.team])
		coords=[int(element) for tupl in self.graphic for element in tupl]
		coords=map(int,map(sum,zip(coords,(self.x,self.y)*3)))

		coords.append(planetfillcolors[self.team])
		gfxdraw.aatrigon(screen,*coords)
		
		#gfxdraw.filled_circle(screen, int(self.x), int(self.y), self.radius, planetfillcolors[self.team])
		#gfxdraw.aacircle(screen, int(self.x), int(self.y), self.radius, planetfillcolors[self.team])
				
class Fleet(object):
	"""Each fleet is a list of Boid objects that move and behave independently, other than an urge to not get too close to any one ship, and an urge to
	move towards the average position of the fleet."""
	def __init__(self,start,end,power,team):
		"""start, end are Planet objects
		time is the number of seconds to their destination
		power is the size of the fleet"""
		self.end=end
		self.team=team
		
		#power/ship  = totalpower/MAX_NUMBER_OF_SHIPS
		#ship/power = MAX_NUMBER_OF_SHIPS/totalpower
		#number of ships to send = MAX_NUMBER_OF_SHIPS*power/totalpower
		
		powerpership=int(math.floor(totalpower/MAX_NUMBER_OF_SHIPS))
		shipstosend=int(math.floor(MAX_NUMBER_OF_SHIPS*power/totalpower))
		
		
		if powerpership<1:
			self.ships=[Boid(start,end,1,team) for i in range(0,power)]
		else:
			self.ships=[Boid(start,end,int(math.floor(powerpership)),team) for i in range(0,int(shipstosend))]
			self.ships.append(Boid(start,end,power%(powerpership),team))
		
		
		
		
	def update(self,dt):
		"""For each ship in the fleet, calculates the acceleration of each ship in the fleet, then the new velocity, then the new position.
		Returns -1 if no ships remain, and 0 if ships do remain."""
		
		#acceleration reset
		for s in self.ships:
			s.ax=0
			s.ay=0	

		for s in self.ships:
			"""Each boid repels each other boid within REPULSION_DISTANCE with a force inversely proportional to the square distance between them.
			Note that we first use square approximation to the REPULSION_DISTANCE circle, then double-check with a circle."""
			for o in self.ships[:self.ships.index(s)]:
				if abs(s.x-o.x)<REPULSION_DISTANCE and abs(s.y-o.y)<REPULSION_DISTANCE:
					square=(s.x-o.x)**2 + (s.y-o.y)**2
					square=square**2
					if square==0:
						s.x+=1
						square=0.00001
					if square<REPULSION_DISTANCE**4:
						s.ax-=REPULSION_CONSTANT*(o.x-s.x)/square
						o.ax-=REPULSION_CONSTANT*(s.x-o.x)/square
						s.ay-=REPULSION_CONSTANT*(o.y-s.y)/square
						o.ay-=REPULSION_CONSTANT*(s.y-o.y)/square
			"""Each planet repels all nearby ships with force that scales exponentially as the ship grows closer."""
			for p in planets:
				if p!=s.end:
					if abs(s.x-p.x)<p.radius+PLANETARY_TOLERANCE and abs(s.y-p.y)<p.radius+PLANETARY_TOLERANCE:
						square=(s.x-p.x)**2 + (s.y-p.y)**2
						dist=math.sqrt(square)
						if square==0:
							pass
						#else:
						elif square<(p.radius+PLANETARY_TOLERANCE)**2:
							s.ax-=PLANETARY_REPULSION_CONSTANT*(PLANETARY_REPULSION_BASE**(p.radius-dist))*(p.x-s.x)/square
							s.ay-=PLANETARY_REPULSION_CONSTANT*(PLANETARY_REPULSION_BASE**(p.radius-dist))*(p.y-s.y)/square
		"""Finally, each fleet attracts all member ships to the average position of the fleet."""
		average_x=sum([s.x for s in self.ships])/len(self.ships)
		average_y=sum([s.y for s in self.ships])/len(self.ships)
		for s in self.ships:
			square=(average_x-s.x)**2 + (average_y-s.y)**2
			if square!=0:
				s.ax+=RESTORATIVE_CONSTANT*(average_x-s.x)*2/square
				s.ay+=RESTORATIVE_CONSTANT*(average_y-s.y)*2/square



		for s in self.ships:
			s.normalizeAcceleration()
			s.vx+=s.ax*dt
			s.vy+=s.ay*dt
			
			d=distance((s.x,s.y),(s.end.x,s.end.y))
			if d !=0:
				factor=dt*SHIPACCEL/d
			s.vx+=factor*(s.end.x-s.x)
			s.vy+=factor*(s.end.y-s.y)
			s.normalizeAcceleration()


		for shipid in range(len(self.ships)-1,-1,-1):
			if self.ships[shipid].update(dt)==-1:
				self.ships.pop(shipid)
		
		if len(self.ships)==0:
			return -1
		return 0
	
	def draw(self,screen):
		for ship in self.ships:
			ship.draw(screen)

#various AIs and stuff
class Player(object):
	def __init__(self,gameworld,team,name=None):
		self.gameworld=gameworld
		self.team=team
		if name!=None:
			self.name=name
		else:
			self.name="Player "+str(team)
	def inp(self):
		pass

class MainPlayer(Player):
	"""The class for the user who is, like, actually controlling the game with the keyboard and stuff."""
	def __init__(self,gameworld,team,name=None):
		Player.__init__(self,gameworld,team,name)
		self.selected=[]
		self.sendpercent=0.5
		self.oldmousepos=None
		
	def inp(self):
		global run
		for event in pygame.event.get():
			if event.type==pygame.KEYDOWN and (event.key==pygame.K_SPACE or event.key==pygame.K_ESCAPE):
				self.gameworld.paused=not self.gameworld.paused

			if event.type==pygame.QUIT:
				run=False

			elif self.team!=-1:
				mousepos=pygame.mouse.get_pos()		
				if event.type==pygame.KEYDOWN:
					if event.key==pygame.K_q:
						self.sendpercent=0.1
					elif event.key==pygame.K_w:
						self.sendpercent=0.5
					elif event.key==pygame.K_e:
						self.sendpercent=1.0

				if event.type==pygame.MOUSEBUTTONDOWN:
					if event.button==1:
						self.selected=[]
						self.oldmousepos=mousepos
						tmp=self.gameworld.intersectingPlanet(mousepos)
						if tmp:
							if tmp.team==1:
								self.selected=[tmp]

				if event.type==pygame.MOUSEMOTION:
					if self.oldmousepos:
						s=[p for p in self.gameworld.planets if intersect((p.x,p.y),p.radius,self.oldmousepos,mousepos) and p.team==self.team]
						#s=[p for p in self.planets if intersect((p.x,p.y),p.radius,self.oldmousepos,mousepos) and p.team==1]
						tmp=self.gameworld.intersectingPlanet(self.oldmousepos)
						if tmp not in s and tmp:
							if tmp.team==1:
								s.append(tmp)
						self.selected=[p for p in s if p.team==1]

				if event.type==pygame.MOUSEBUTTONUP:
					if event.button==1:
						self.oldmousepos=None
					if event.button==3:
						other=self.gameworld.intersectingPlanet(mousepos)
						if len(self.selected)>0 and other!=None:
							for s in self.selected[::-1]:
								if s.team==self.team:
									if s.power>=1:
										tentative=int(s.power*self.sendpercent)
										if tentative==0:
											tentative=1
										self.gameworld.sendfleet(s,other,tentative)
								else:
									self.selected.remove(s)
			keys=pygame.key.get_pressed()
		else:
			for event in pygame.event.get():
				if event.type==pygame.QUIT:
					run=False

class StupidPlayer(Player):
	"""Every frame, picks a random friendly planet and a random enemy planet. If possible, it then sends exactly the number of ships necessary for capture."""
	def inp(self):
		friendlies=[p for p in self.gameworld.planets if p.team==self.team]
		enemies=[p for p in self.gameworld.planets if p.team!=self.team]
		if friendlies and enemies and random.uniform(0,1)<AI_TEMPO:
			start=random.choice(friendlies)
			end=random.choice(enemies)
			if end.team==0:
				if start.power>(end.power+4):
					self.gameworld.sendfleet(start,end,int(math.ceil(end.power+3)))
			else:
				t=(distance((start.x,start.y),(end.x,end.y))/MAXSPEED)
				req=(end.power+(end.growth*t))*1.1
				if start.power>(req):
					self.gameworld.sendfleet(start,end,int(math.ceil(req)))

class GameWorld(object):
	def __init__(self,screen,ai=False):
		global planets
		global totalpower
		totalpower=1
		planets=[]
		self.planets=planets
		self.fleets=[]
		self.screen=screen
		self.paused=True

		if ai:
			self.mainplayer=MainPlayer(self,-1)
			self.players=[self.mainplayer]
			self.players.append(StupidPlayer(self,1))
			self.players.append(StupidPlayer(self,2))
		
		else:
			self.mainplayer=MainPlayer(self,1)
			self.players=[self.mainplayer]
			self.players.append(StupidPlayer(self,2))

		
	def seedplanets(self,n,tolerance,maxpower,distro):
		"""Distro is a list of "specifier" 3-tuples, containing (frequency,radius,growth)"""
		if n%2 ==1:
			d=choosefromdistribution(distro)
			self.planets.append(Planet((self.screen.get_width()/2,self.screen.get_height()/2),d[1],d[2],random.randint(1,maxpower),0))
		for i in range(n/2):
			placed=False
			while not placed:
				d=choosefromdistribution(distro)
				
				x=random.randint(d[1],self.screen.get_width()-d[1])
				y=random.randint(d[1],self.screen.get_height()-d[1])
				power=random.randint(1,maxpower)
				if all([distance((x,y),(op.x,op.y))>(d[1]+op.radius+tolerance) for op in self.planets]):
					self.planets.append(Planet((x,y),d[1],d[2],power,0))
					self.planets.append(Planet((self.screen.get_width()-x,self.screen.get_height()-y),d[1],d[2],power,0))
					placed=True
	
	def sendfleet(self,start,end,power):
		if start!=end:
			self.fleets.append(Fleet(start,end,int(power),start.team))
			start.power-=int(power)
	
	def clear(self):
		self.__init__(self.screen)

	def update(self,dt):
		for player in self.players:
			player.inp()
		
		dt*=2

		if not self.paused:
			for planetid in range(len(self.planets)-1,-1,-1):
				self.planets[planetid].update(dt)
			
			for fleetid in range(len(self.fleets)-1,-1,-1):
				if self.fleets[fleetid].update(dt)==-1:
					self.fleets.pop(fleetid)

	def intersectingPlanet(self,(x,y)):
		for p in self.planets:
			if distance((x,y),(p.x,p.y))<p.radius:
				return p
	
	def friendlyContainedPlanets(self,(x1,y1),(x2,y2)):
		return [p for p in self.containedPlanets((x1,y1),(x2,y2)) if p.team==1]

	def containedPlanets(self,(x1,y1),(x2,y2)):
		"""upper left, bottom right"""
		if x1>x2:
			x1,x2=x2,x1
		if y1>y2:
			y1,y2=y2,y1
		return [p for p in self.planets if x1<p.x and p.x<x2 and y1<p.y and p.y<y2]

	def drawselectionbox(self,screen):
		if self.mainplayer.oldmousepos:
			m=pygame.mouse.get_pos()
			x=self.mainplayer.oldmousepos[0]
			y=self.mainplayer.oldmousepos[1]
			w=m[0]-x
			h=m[1]-y
			gfxdraw.rectangle(screen,pygame.Rect(x,y,w,h),selectedcolor)

	def draw(self):
		global BLINDMODE
		for s in self.mainplayer.selected:
			gfxdraw.aacircle(self.screen,s.x,s.y,s.radius+5,selectedcolor)
			gfxdraw.filled_circle(self.screen,s.x,s.y,s.radius+5,selectedcolor)
		
			gfxdraw.aacircle(self.screen,s.x,s.y,s.radius+3,(0,0,0))
			gfxdraw.filled_circle(self.screen,s.x,s.y,s.radius+3,(0,0,0))
		
		for planet in self.planets:
			planet.draw(self.screen)
			if not BLINDMODE:
				planet.drawpower(self.screen)
			else:
				if planet.team==self.mainplayer.team or planet.team==0:
					planet.drawpower(self.screen)
		for fleet in self.fleets:
			fleet.draw(self.screen)
		self.drawselectionbox(self.screen)
		if self.paused:
			pause=pygame.Rect(0,0,30,100)
			pause.center=map(lambda l:l/2,self.screen.get_size())
			pause.x-=30
			pygame.draw.rect(self.screen,(255,255,255),pause)
			pause.x+=60
			pygame.draw.rect(self.screen,(255,255,255),pause)

def main(argv):
	global myfont
	global planetfillcolors, planetbordercolors, selectedcolor
	global run
	
	size=(1000,700)	#width, height of window
	fps=60
	aimode=False
	numplanets=41

	i=0
	try:
		while i<len(argv):
			global AI_TEMPO

			if argv[i]=="-help":
				print documentation
				return
			elif argv[i]=="-fps":
				fps=int(argv[i+1])
				assert fps>0
				i+=1
			elif argv[i]=="-ai":
				aimode=True
			elif argv[i]=="-aitempo":
				AI_TEMPO=float(argv[i+1])
				assert 0<=AI_TEMPO and AI_TEMPO<=1
				i+=1
			elif argv[i]=="-pacifist":
				AI_TEMPO=-1
			elif argv[i]=="-shipspeed":
				global MAXSPEED,SHIPACCEL,MAXACCEL,REPULSION_CONSTANT
				k=int(argv[i+1])/float(MAXSPEED)
				SHIPACCEL*=k
				MAXACCEL*=k
				REPULSION_CONSTANT*=k
				MAXSPEED=int(argv[i+1])

				assert MAXSPEED>0
				i+=1
			elif argv[i]=="-maxships":
				global MAXSHIPS
				MAXSHIPS=int(argv[i+1])/MAXSPEED
				assert MAXSHIPS>0
				i+=1
			elif argv[i]=="-blindmode":
				global BLINDMODE
				BLINDMODE=True
			elif argv[i]=="-size":
				size=int(argv[i+1]),int(argv[i+2])
				i+=2
			elif argv[i]=="-planets":
				numplanets=int(argv[i+1])
				assert numplanets>0
				i+=1
			else:
				raise KeyError
			i+=1

	except KeyError:
		print "unknown argument:",argv[i]
		return
	except IndexError:
		print "expected argument not found"
		return
	except AssertionError:
		print "invalid argument, see -help for details"
		return

	planetfillcolors=(100,100,100),(0,200,0),(200,0,0)
	planetbordercolors=(50,50,50),(0,100,0),(100,0,0)
	selectedcolor=(100,100,255)

	pygame.init()
	myfont = pygame.font.SysFont("monospace", 15)
	
	
	screen = pygame.display.set_mode(size)
	pygame.display.set_caption("Definitely Not Galcon - Jasper Chapman-Black")
	run = True
	clock = pygame.time.Clock()
	oldtime=0.

	#GAMEWORLD SETUP
	gameworld=GameWorld(screen,ai=aimode)
	gameworld.seedplanets(numplanets,20,40,( \
		(3,25,2),	#small planets 
		(3,35,4),	#medium planets
		(1,50,100)	#large planets

		))
	start=random.randint(1,(len(gameworld.planets))/2 - 3)
	if len(gameworld.planets)%2==0:
		gameworld.planets[0].team=1
		gameworld.planets[1].team=2
	else:
		gameworld.planets[2*start].team=1
		gameworld.planets[(2*start)-1].team=2
	gameworld.paused=True

	while run:
		currenttime=pygame.time.get_ticks()/1000.		#all in seconds
		deltatime=(currenttime-oldtime)
		oldtime=currenttime
		
		gameworld.update(deltatime)
		
		screen.fill((0,0,0))
		gameworld.draw()

		#rendering
		pygame.display.flip()
		clock.tick(fps)


if __name__=="__main__":
	main(sys.argv[1:])
