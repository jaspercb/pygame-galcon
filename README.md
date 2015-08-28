# pygame-galcon
implementation of galcon using pygame

#Controls:
  left-click to select a friendy planet, or drag to select several

  right-click a planet to attack with fleets from selected planets
  
  space to pause


#Command Line Arguments:
  -help		useful information on command line arguments

  -fps x	sets max fps to x (x>0)

  -ai		sets game mode to a match between two AIs

  -aitempo x	alters ai rate. as x approaches 1, ai reacts faster

  -pacifist		enemies don't do anything

  -shipspeed x	sets maximum ship speed, in px/s. default is 50

  -maxships x	sets soft cap on number of ships displayed

  -blindmode	hides enemy power levels because the game isn't hard enough

  -size w h		sets screen width, height

#Suggested Useful Game Modes:
  
  -aitempo 1 -ai -shipspeed 250 -maxships 1000