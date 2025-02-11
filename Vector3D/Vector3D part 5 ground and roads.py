# -*- coding: utf-8 -*-
import pygame
import numpy as np
import math
import os
from operator import itemgetter
import copy
import xml.etree.ElementTree as et

key_to_function = {
    pygame.K_ESCAPE: (lambda x: x.terminate()),         # ESC key to quit
    pygame.K_SPACE:  (lambda x: x.pause())              # SPACE to pause
    }

class VectorViewer:
    """
    Displays 3D vector objects on a Pygame screen.
    
    @author: kalle
    """

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width,height))
        self.use_gfxdraw = False                         # pygame.gfxdraw is "experimental" and may be discontinued.
        self.fullScreen = False
        pygame.display.set_caption('VectorViewer')
        self.backgroundColor = (0,0,0)
        self.VectorAnglesList = []
        self.viewerAngles = VectorAngles()
        self.VectorObjs = []
        self.VectorObjPrios = []
        self.VectorPos = VectorPosition()
        self.midScreen = np.array([width / 2, height / 2], dtype=float)
        self.zScale = width * 0.7                       # Scaling for z coordinates
        self.objMinZ = 100.0                            # minimum z coordinate for object visibility
        self.groundZ = 64000.0                          # for a ground object, maximum distance in Z
        self.groundShades = (15.0,100.0)                # ground color strength (in percentage) at groundZ and at 0 Z
        self.groundShadeNr = 16                         # number of ground elements with different shading
        self.groundColors = []                          # ground colors used based on object color and groundShadeNr
        self.groundObject = None
        self.lightPosition = np.array([400.0, 800.0, -500.0])
        self.target_fps = 60                            # affects movement speeds
        self.running = True
        self.paused = False
        self.clock = pygame.time.Clock()
            
    def setVectorPos(self, VectorPosObj):
        self.VectorPos = VectorPosObj
             
    def addVectorObj(self, VectorObj):
        self.VectorObjs.append(VectorObj)
       
    def addVectorAnglesList(self, VectorAngles):
        self.VectorAnglesList.append(VectorAngles)

    def run(self):
        """ Main loop. """
                  
        for VectorObj in self.VectorObjs:
            VectorObj.initObject() # initialize objects

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in key_to_function:
                        key_to_function[event.key](self)
            
            if self.paused == True:
                pygame.time.wait(100)
            
            else:
                # main components executed here
                self.rotate()
                self.calculate()
                self.display()
                
                # release any locks on screen
                while self.screen.get_locked():
                    self.screen.unlock()
                    
                # switch between currently showed and the next screen (prepared in "buffer")
                pygame.display.flip()
                self.clock.tick(self.target_fps) # this keeps code running at max target_fps

        # exit; close display, stop music
        pygame.display.quit()
                                                         
    def rotate(self):
        """ 
        Rotate all objects. First calculate rotation matrix.
        Then apply the relevant rotation matrix with object position to each VectorObject.
        """
                
        # calculate rotation matrices for all angle sets
        for VectorAngles in self.VectorAnglesList:
            VectorAngles.setRotateAngles()
            VectorAngles.setRotationMatrix()
        
        # rotate object positions, copy those to objects.
        self.VectorPos.rotate() 
        for (node_num, VectorObj) in self.VectorPos.objects:
            VectorObj.setPosition(self.VectorPos.rotatedNodes[node_num, :])

        # rotate and flatten (transform) objects
        for VectorObj in self.VectorObjs:
            VectorObj.updateVisiblePos(self.objMinZ) # test for object position Z
            if VectorObj.visible == 1:
                VectorObj.rotate(self.viewerAngles) # rotates objects in 3D
                VectorObj.updateVisibleNodes(self.objMinZ) # test for object minimum Z
                if VectorObj.visible == 1:
                    VectorObj.transform(self.midScreen, self.zScale, self.objMinZ) # flattens to 2D
                    VectorObj.updateVisibleTrans(self.midScreen) # test for outside of screen
            
    def calculate(self):
        """ 
        Calculate shades and visibility. 
        """

        for VectorObj in (vobj for vobj in self.VectorObjs if vobj.visible == 1 and vobj != self.groundObject):
            # calculate angles to Viewer (determines if surface is visible) and LightSource (for shading)
            VectorObj.updateSurfaceZPos()
            VectorObj.updateSurfaceCrossProductVector()
            VectorObj.updateSurfaceAngleToViewer()
            VectorObj.updateSurfaceAngleToLightSource(self.lightPosition)
            VectorObj.updateSurfaceColorShade()
       
    def display(self):
        """ 
        Draw the VectorObjs on the screen. 
        """

        # lock screen for pixel operations
        self.screen.lock()

        # clear screen. If ground object is used, do clearing there. 
        if self.groundObject is None:
            self.screen.fill(self.backgroundColor)
                   
        # first sort VectorObjs so that the most distant is first, but prio classes separately.
        # prio classes allow e.g. to draw all roads first and only then other objects
        self.VectorObjs.sort(key=lambda VectorObject: (VectorObject.prio, VectorObject.position[2]), reverse=True)
        
        # draw prio by prio
        for prio_nr in self.VectorObjPrios:

            # draw the actual objects
            for VectorObj in (vobj for vobj in self.VectorObjs if vobj.visible == 1 and vobj.prio == prio_nr):

                if VectorObj == self.groundObject:
                    # special object to add ground data
                    transNodes = VectorObj.groundData(self.midScreen, self.zScale, self.objMinZ, self.groundZ, self.groundShades, self.groundShadeNr)
                    # draw ground. transNodes is of shape(groundShadeNr + 1, 4) and each row has two (left & right) X,Y coordinates
                    # the first component is not part of the ground but used to clear the rest of the screen
                    surface = VectorObj.surfaces[0]  # just one ground surface                      
                    for i in range(self.groundShadeNr + 1):
                        node_list = self.cropEdges([transNodes[i,0:2], transNodes[i,2:4], transNodes[i+1,2:4], transNodes[i+1,0:2]], False, True) # X already cropped
                        self.drawPolygon(self.groundColors[i], node_list, surface.edgeWidth)
                   
                else:
                    if VectorObj.isFlat == 1:
                        # flat objects have a single surface and a prebuilt list of transNodes
                        surface = VectorObj.surfaces[0]
                        node_list = self.cropEdges(VectorObj.transNodes)
                        self.drawPolygon(surface.colorRGB(), node_list, surface.edgeWidth)
                    else:
                        # first sort object surfaces so that the most distant is first. For concave objects there should be no overlap, though.
                        VectorObj.sortSurfacesByZPos()
                        # then draw surface by surface. This is the most common case, the above are for special objects.
                        for surface in (surf for surf in VectorObj.surfaces if surf.visible == 1):
                            # build a list of transNodes for this surface
                            node_list = ([VectorObj.transNodes[node][:2] for node in surface.nodes])
                            self.drawPolygon(surface.colorRGB(), node_list, surface.edgeWidth)       
        
        # unlock screen
        self.screen.unlock()

    def cropEdges(self, node_list, cropX = True, cropY = True):
        # crop to screen size. "Auto crop" does not seem to work if points very far outside.
        # takes list of nodes (X,Y) in drawing order as input.
        # returns list of nodes (X,Y) cropped to screen edges.
        # crop both X, Y, if cropX and cropY = True; X: i=0, Y: i=1
        if len(node_list) > 2:
            for i in range(2):
                if (i == 0 and cropX == True) or (i == 1 and cropY == True):
                    crop_nodes = [] # empty list
                    prev_node = node_list[-1]
                    for node in node_list:
                        diff_node = node - prev_node # surface side vector
                        # start cropping from prev_node direction, as order must stay the same
                        if node[i] >= 0 and prev_node[i] < 0:
                            # line crosses 0, so add a "crop point". Start from previous node and add difference stopping to 0
                            crop_nodes.append(prev_node + diff_node * ((0 - prev_node[i]) / diff_node[i]))
                        if node[i] <= self.midScreen[i] * 2 and prev_node[i] > self.midScreen[i] * 2:
                            # line crosses screen maximum, so add a "crop point". Start from previous node and add difference stopping to midScreen[i] * 2
                            crop_nodes.append(prev_node + diff_node * ((self.midScreen[i] * 2 - prev_node[i]) / diff_node[i]))
                        # then crop current node
                        if node[i] < 0 and prev_node[i] >= 0:
                            # line crosses 0, so add a "crop point". Start from previous node and add difference stopping to 0
                            crop_nodes.append(prev_node + diff_node * ((0 - prev_node[i]) / diff_node[i]))
                        if node[i] > self.midScreen[i] * 2 and prev_node[i] <= self.midScreen[i] * 2:
                            # line crosses screen maximum, so add a "crop point". Start from previous node and add difference stopping to midScreen[i] * 2
                            crop_nodes.append(prev_node + diff_node * ((self.midScreen[i] * 2 - prev_node[i]) / diff_node[i]))         
                        # always add current node, if it is on screen
                        if node[i] >= 0 and node[i] <= self.midScreen[i] * 2:
                            crop_nodes.append(node)
                        prev_node = node
                    # for next i, copy results. Quit loop if no nodes to look at
                    node_list = crop_nodes
                    if len(node_list) < 3:
                        break               
            # convert to integers
            node_list = [(int(x[0] + 0.5), int(x[1] + 0.5)) for x in node_list]
        return node_list
                              
    def drawPolygon(self, color, node_list, edgeWidth):

        if len(node_list) > 2: # a polygon needs at least 3 nodes
            if self.use_gfxdraw  == True:
                pygame.gfxdraw.aapolygon(self.screen, node_list, color)                               
                pygame.gfxdraw.filled_polygon(self.screen, node_list, color)                               
            else:
                pygame.draw.aalines(self.screen, color, True, node_list)       
                pygame.draw.polygon(self.screen, color, node_list, edgeWidth)       
                
    def terminate(self):

        self.running = False   

    def pause(self):

        if self.paused == True:
            self.paused = False
        else:
            self.paused = True
       
class VectorObject:

    """
    Position is the object's coordinates.
    Nodes are the predefined, static definition of object "corner points", around object position anchor point (0,0,0).
    RotatedNodes are the Nodes rotated by the given Angles and moved to Position.
    TransNodes are the RotatedNodes transformed from 3D to 2D (X.Y) screen coordinates.
    
    @author: kalle
    """
    def __init__(self):
        self.position = np.array([0.0, 0.0, 0.0, 1.0])      # position
        self.nodePosition = np.array([0.0, 0.0, 0.0, 1.0])  # position before rotation
        self.angles = VectorAngles()
        self.nodes = np.zeros((0, 4))                       # nodes will have unrotated X,Y,Z coordinates plus a column of ones for position handling
        self.objRotatedNodes = np.zeros((0, 3))             # objRotatedNodes will have X,Y,Z coordinates after object rotation in place (object angles)
        self.rotatedNodes = np.zeros((0, 3))                # rotatedNodes will have X,Y,Z coordinates after rotation ("final 3D coordinates")
        self.transNodes = np.zeros((0, 2))                  # transNodes will have X,Y coordinates
        self.surfaces = []
        self.visible = 1
        self.isFlat = 0
        self.prio = 0                                       # priority order when drawn. Highest prio will be drawn first
        self.objName = ""
        self.minShade = 0.2                                 # shade (% of color) to use when surface is parallel to light source

    def initObject(self):
        self.updateSurfaceZPos()
        self.updateSurfaceCrossProductVector()
        self.updateSurfaceCrossProductLen()

    def setPosition(self, position):
        # move object by giving it a rotated position.
        self.position = position 

    def setFlat(self):
        # set isFlat
        self.isFlat = 1 

    def addNodes(self, node_array):
        # add nodes (all at once); add a column of ones for using position in transform
        self.nodes = np.hstack((node_array, np.ones((len(node_array), 1))))
        self.rotatedNodes = node_array # initialize rotatedNodes with nodes (no added ones required)

    def addSurfaces(self, idnum, color, edgeWidth, showBack, backColor, node_list):
        # add a Surface, defining its properties
        surface = VectorObjectSurface()
        surface.idnum = idnum
        surface.color = color
        surface.edgeWidth = edgeWidth
        surface.showBack = showBack
        surface.backColor = backColor
        surface.nodes = node_list
        self.surfaces.append(surface)
    
    def updateVisiblePos(self, objMinZ):
        # check if object is visible. If any of node Z coordinates are too close to viewer, set to 0, unless is flat
        if self.isFlat == 0 and self.position[2] < objMinZ: 
            self.visible = 0
        else:
            self.visible = 1

    def updateVisibleNodes(self, objMinZ):
        # check if object is visible. If any of node Z coordinates are too close to viewer, set to 0, unless is flat
        if self.isFlat == 0:
            if min(self.rotatedNodes[:, 2]) < objMinZ: 
                self.visible = 0
            else:
                self.visible = 1
        else:
            # for flat objects, check if the whole object is behind the viewing point (minZ)
            if max(self.rotatedNodes[:, 2]) < objMinZ:
                self.visible = 0
            else:
                self.visible = 1

    def updateVisibleTrans(self, midScreen):
        # check if object is visible. If not enough nodes or all X or Y coordinates are outside of screen, set to 0
        if \
            np.shape(self.transNodes)[0] < 3 \
            or max(self.transNodes[:, 0]) < 0 \
            or min(self.transNodes[:, 0]) > midScreen[0] * 2 \
            or max(self.transNodes[:, 1]) < 0 \
            or min(self.transNodes[:, 1]) > midScreen[1] * 2:
            self.visible = 0
        else:
            self.visible = 1

    def updateSurfaceZPos(self):
        # calculate average Z position for each surface using rotatedNodes
        for surface in self.surfaces:
            zpos = sum([self.rotatedNodes[node, 2] for node in surface.nodes]) / len(surface.nodes) 
            surface.setZPos(zpos)
            surface.setVisible(1) # set all surfaces to "visible" 
        
    def updateSurfaceCrossProductVector(self):
        # calculate cross product vector for each surface using rotatedNodes
        # always use vectors (1, 0) and (1, 2) (numbers representing nodes)
        # numpy "cross" was terribly slow, calculating directly as below takes about 10 % of the time.
        for surface in self.surfaces:
            vec_A = self.rotatedNodes[surface.nodes[2], 0:3] - self.rotatedNodes[surface.nodes[1], 0:3]
            vec_B = self.rotatedNodes[surface.nodes[0], 0:3] - self.rotatedNodes[surface.nodes[1], 0:3]
            vec_Cross =  ([
                vec_B[1] * vec_A[2] - vec_B[2] * vec_A[1],
                vec_B[2] * vec_A[0] - vec_B[0] * vec_A[2],
                vec_B[0] * vec_A[1] - vec_B[1] * vec_A[0]
                ])
            surface.setCrossProductVector(vec_Cross)

    def updateSurfaceCrossProductLen(self):
        # calculate cross product vector length for each surface.
        # this is constant and done only at init stage.
        for surface in self.surfaces:
            surface.setCrossProductLen()

    def updateSurfaceAngleToViewer(self):
        # calculate acute angle between surface plane and Viewer
        # surface plane cross product vector and Viewer vector both from node 1.
        for surface in (surf for surf in self.surfaces if surf.visible == 1):
            vec_Viewer = self.rotatedNodes[surface.nodes[1], 0:3] 
            surface.setAngleToViewer(vec_Viewer)
            if surface.angleToViewer > 0 or surface.showBack == 1:
                surface.setVisible(1)
            else:
                surface.setVisible(0)

    def updateSurfaceAngleToLightSource(self, lightPosition):
        # calculate acute angle between surface plane and light source, similar to above for Viewer.
        # this is used to define shading and shadows; needed for visible surfaces using shading AND all surfaces, if shadow to be drawn.
        for surface in (surf for surf in self.surfaces if surf.visible == 1 and self.minShade < 1.0):
            surface.setLightSourceVector(self.rotatedNodes[surface.nodes[1], 0:3] - lightPosition)
            surface.setAngleToLightSource()

    def updateSurfaceColorShade(self):
        # calculate shade for surface. 
        for surface in (surf for surf in self.surfaces if surf.visible == 1):
            surface.setColorShade(self.minShade)
            if surface.showBack == 1: surface.setBackColorShade(self.minShade)

    def sortSurfacesByZPos(self):
        # sorts surfaces by Z position so that the most distant comes first in list
        self.surfaces.sort(key=lambda VectorObjectSurface: VectorObjectSurface.zpos, reverse=True)

    def rotate(self, viewerAngles):
        """ 
        Apply a rotation defined by a given rotation matrix.
        For objects with their own angles / rotation matrix, apply those first and store results in objRotatedNodes.
        Could be done in one step but objRotatedNodes needed for shadow calculations.
        """
        if self.angles != viewerAngles:
            # rotate object with its own angles "in place" ie. with synthetic zero vector as position
            matrix = np.vstack((self.angles.rotationMatrix, np.zeros((1,3))))
            self.objRotatedNodes = np.dot(self.nodes, matrix)
        else:
            # no own angles, just copy nodes then
            self.objRotatedNodes = self.nodes[:,0:3]
        # then rotate with viewer angles. Add position to rotation matrix to enable both rotation and position change at once
        matrix = np.vstack((viewerAngles.rotationMatrix, self.position[0:3]))
        self.rotatedNodes = np.dot(np.hstack((self.objRotatedNodes, np.ones((np.shape(self.objRotatedNodes)[0], 1)))), matrix)

    def transform(self, midScreen, zScale, objMinZ):
        """ 
        Flatten from 3D to 2D and add screen center.
        First crop flat objects by Z coordinate so that they can be drawn even if some Z coordinates are behind the viewer.
        """
        if self.isFlat == 1:
            # for flat objects, build a list of transNodes for the surface by first cropping the necessary surface sides to minZ
            for surface in self.surfaces:
                surface.setVisible(1) # set all surfaces to "visible" 
                flat_nodes = np.zeros((0, 3))
                for node_num in range(len(surface.nodes)):
                    node = self.rotatedNodes[surface.nodes[node_num], 0:3] # current node XYZ coordinates
                    prev_node = self.rotatedNodes[surface.nodes[node_num - 1], 0:3] # previous node XYZ coordinates
                    diff_node = node - prev_node # surface side vector
                    # if both Z coordinates behind the viewer: do not draw at all, do not add a transNode
                    if (node[2] < objMinZ and prev_node[2] >= objMinZ) or (node[2] >= objMinZ and prev_node[2] < objMinZ):
                        # line crosses objMinZ, so add a "crop point". Start from previous node and add difference stopping to objMinZ
                        flat_nodes = np.vstack((flat_nodes, prev_node + diff_node * ((objMinZ - prev_node[2]) / diff_node[2])))
                    if node[2] >= objMinZ:
                        # add current node, if it is visible
                        flat_nodes = np.vstack((flat_nodes, node))
                # apply perspective using Z coordinates and add midScreen to center on screen to get to transNodes
                self.transNodes = (-flat_nodes[:, 0:2] * zScale) / (flat_nodes[:, 2:3]) + midScreen
        else:            
            # apply perspective using Z coordinates and add midScreen to center on screen to get to transNodes.
            # for normal objects, some of the transNodes will not be required, but possibly figuring out which are and processing them
            #   individually could take more time than this.
            self.transNodes = (self.rotatedNodes[:, 0:2] * zScale) / (-self.rotatedNodes[:, 2:3]) + midScreen

    def groundData(self, midScreen, zScale, objMinZ, groundZ, groundShades, groundShadeNr):
        """ 
        Calculate ground data for on a ground object.
        Assumes the ground object "covers the ground" reasonably and isFlat = 1, and the perimeter is concave.
        Ground settings are defined in VectorViewer.
        Returns an array of shape(groundShadeNr + 1, 4) where each row has X,Y of left edge and X.Y of right edge starting from most distant
        """
        # find the most distant node
        maxZ = max(self.rotatedNodes[:, 2])
        for nodenum in range(len(self.nodes)):
            if self.rotatedNodes[nodenum, 2] == maxZ:
                node = self.rotatedNodes[nodenum, :]
                break
        prev_node = self.rotatedNodes[nodenum - 1, :]
        if nodenum == len(self.nodes) - 1:
            next_node = self.rotatedNodes[0, :]
        else:
            next_node = self.rotatedNodes[nodenum + 1, :]
            
        # get a straight line where Z (ie, distance from viewer) is constant. Start with the mid of farthest of the two lines.
        # then find the point with matching Z coordinate on the other line.
        # special cases: next_node or prev_node as far as node.
        if node[2] == prev_node[2]:
            mid1_node = node
            mid2_node = prev_node
        else:
            if node[2] == next_node[2]:
                mid1_node = node
                mid2_node = next_node
            else:
                if next_node[2] > prev_node[2]:
                    mid1_node = (next_node + node) / 2
                    mid2_node = node + (prev_node - node) * (mid1_node[2] - node[2]) / (prev_node[2] - node[2])
                else:
                    mid1_node = (prev_node + node) / 2
                    mid2_node = node + (next_node - node) * (mid1_node[2] - node[2]) / (next_node[2] - node[2])
        if mid1_node[1] < mid2_node[1]:
            # make sure mid1_node X < mid2_node X
            mid1_node, mid2_node = mid2_node, mid1_node
        # adjust Z
        mid1_node = mid1_node * groundZ / mid1_node[2]
        mid2_node = mid2_node * groundZ / mid2_node[2]
        # finalize a square around object position
        mid2_node_back = self.position[0:3] + (self.position[0:3] - mid1_node) # from front left (mid1) to back right (mid2_back)
        mid1_node_back = self.position[0:3] + (self.position[0:3] - mid2_node) # from front right (mid2) to back left (mid1_back)

        # then generate arrays with necessary node data and transNode data
        left_nodes = np.zeros((groundShadeNr + 1, 3), dtype=float)
        right_nodes = np.zeros((groundShadeNr + 1, 3), dtype=float)
        # multipliers will span ground component span between groundZ/2 (furthest) and objMinZ
        mult = (mid1_node[2] / 2 - objMinZ) / ((mid1_node[2] - mid1_node_back[2]) / 2)
        # the most distant component (at groundZ). Most distant component will be very large (half of total)
        left_nodes[0,:] = mid1_node  
        right_nodes[0,:] = mid2_node                

        # other components from groundZ/2 to objMinZ
        for i in range(groundShadeNr):
            mult_i =  mult * math.sqrt((i+1) / groundShadeNr)
            left_nodes[i+1,:] = (mid1_node * (1.0 - mult_i) + mid1_node_back * mult_i) / 2
            right_nodes[i+1,:] = (mid2_node * (1.0 - mult_i) + mid2_node_back * mult_i) / 2         
        left_transNodes = (-left_nodes[:, 0:2] * zScale) / (left_nodes[:, 2:3]) + midScreen
        right_transNodes = (-right_nodes[:, 0:2] * zScale) / (right_nodes[:, 2:3]) + midScreen
        
        # crop these nodes to screen X edges
        diff_transNodes = right_transNodes - left_transNodes
        mult_nodes = right_transNodes[:, 0] / diff_transNodes[:, 0] 
        left_transNodes = right_transNodes - np.multiply(np.transpose(np.vstack((mult_nodes, mult_nodes))), diff_transNodes)
        diff_transNodes = right_transNodes - left_transNodes
        mult_nodes = (midScreen[0] * 2) / diff_transNodes[:,0]
        right_transNodes = left_transNodes + np.multiply(np.transpose(np.vstack((mult_nodes, mult_nodes))), diff_transNodes)

        # the first component is "the top of the sky".
        if left_transNodes[0,1] < left_transNodes[1,1]:
            # "normal ground", add a node to the top of the screen
            if left_transNodes[0,1] < 0:
                # if ground already covers the whole screen, use the top node
                left_skynode = left_transNodes[0,:]
            else:
                left_skynode = np.array([0, 0])
        else:
            # inverted ground ie. going upside down, add a node to the bottom of the screen
            if left_transNodes[0,1] > midScreen[1] * 2:
                # if ground already covers the whole screen, use the top node
                left_skynode = left_transNodes[0,:]
            else:
                left_skynode = np.array([0, midScreen[1] * 2])
        if right_transNodes[0,1] < right_transNodes[1,1]:
            # "normal ground", add a node to the top of the screen
            if right_transNodes[0,1] < 0:
                # if ground already covers the whole screen, use the top node
                right_skynode = right_transNodes[0,:]
            else:
                right_skynode = np.array([midScreen[0] * 2, 0])
        else:
            # inverted ground ie. going upside down, add a node to the bottom of the screen
            if right_transNodes[0,1] > midScreen[1] * 2:
                # if ground already covers the whole screen, use the top node
                right_skynode = right_transNodes[0,:]
            else:
                right_skynode = midScreen * 2               
        # add the first component and build an array of all the transnodes
        transNodes = np.vstack((np.hstack((left_skynode, right_skynode)), np.hstack((left_transNodes, right_transNodes))))      
        
        return(transNodes)        
                
class VectorObjectSurface:

    """
    Surfaces for a VectorObject.
    
    @author: kalle
    """
    def __init__(self):
        self.idnum = 0
        # properties set when defining the object
        self.nodes = []
        self.color = (0,0,0)
        self.edgeWidth = 0           # if 0, fills surface. Otherwise a wireframe (edges only), with edgeWidth thickness.
        # the following are calculated during program execution
        self.zpos = 0.0
        self.crossProductVector = np.zeros((0,3))
        self.crossProductLen = 0.0   # precalculated length of the cross product vector - this is constant
        self.lightSourceVector = np.zeros((0,3))
        self.angleToViewer = 0.0
        self.angleToLightSource = 0.0
        self.visible = 1
        self.colorShade = 1.0        # Shade of color; 0 = black, 1 = full color

    def setZPos(self, zpos):
        self.zpos = zpos
 
    def setVisible(self, visible):
        self.visible = visible
        
    def setCrossProductVector(self, crossProductVector):
        self.crossProductVector = crossProductVector

    def setLightSourceVector(self, lightSourceVector):
        self.lightSourceVector = lightSourceVector

    def setCrossProductLen(self):
        self.crossProductLen = self.vectorLen(self.crossProductVector)

    def setAngleToViewer(self, vec_Viewer):
        if self.crossProductLen > 0 and vec_Viewer.any() != 0:
            # instead of true angle calculation using asin and vector lengths, a simple np.vdot is sufficient to find the sign (which defines if surface is visible) 
            # self.angleToViewer = math.asin(np.dot(self.crossProductVector, vec_Viewer) / (self.crossProductLen * np.linalg.norm(vec_Viewer)))
            self.angleToViewer = np.dot(self.crossProductVector, vec_Viewer) 
 
    def setAngleToLightSource(self):
        if self.crossProductLen > 0 and self.lightSourceVector.any() != 0:
            # instead of true angle calculation using asin and vector lengths, a simple np.vdot is sufficient to find the sign (which defines if surface is shadowed) 
            # self.angleToLightSource = math.asin(np.dot(self.crossProductVector, self.lightSourceVector) / (self.crossProductLen * np.linalg.norm(self.lightSourceVector))) / (np.pi / 2)
            self.angleToLightSource = np.dot(self.crossProductVector, self.lightSourceVector)
        
    def setColorShade(self, minShade):
        if self.angleToLightSource <= 0:
            self.colorShade = minShade
        else:
            self.colorShade = minShade + (1.0 - minShade) * math.asin(self.angleToLightSource / (self.crossProductLen * self.vectorLen(self.lightSourceVector))) / (np.pi / 2)
        
    def setBackColorShade(self, minShade):
        if self.angleToLightSource >= 0:
            self.backColorShade = minShade
        else:
            self.backColorShade = minShade + (1.0 - minShade) * -math.asin(self.angleToLightSource / (self.crossProductLen * self.vectorLen(self.lightSourceVector))) / (np.pi / 2)

    def colorRGB(self):
        use_color = ([round(self.colorShade * x, 0) for x in self.color]) # apply shading
        return use_color

    def vectorLen(self, vector):
        # equivalent to numpy.linalg.norm for a 3D real vector, but much faster. math.sqrt is faster than numpy.sqrt.
        return math.sqrt(vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2])

class VectorAngles:

    """
    Angles for rotating vector objects. For efficiency, one set of angles can be used for many objects.
    Angles are defined for axes X (horizontal), Y (vertical), Z ("distance") in degrees (360).
    
    @author: kalle
    """
    def __init__(self):
        self.angles = np.array([0.0, 0.0, 0.0])
        self.angleScale = (2.0 * np.pi) / 360.0 # to scale degrees.
        self.angName = ""
        self.rotationMatrix = np.zeros((3,3))
        self.rotateAngles = np.array([0.0, 0.0, 0.0])
        self.rotate = np.array([0.0, 0.0, 0.0])
    
    def setAngles(self, angles):
        # Set rotation angles to fixed values. 
        self.angles = angles
     
    def setRotateAngles(self):
        self.rotateAngles += self.rotate
        for i in range(3):
            if self.rotateAngles[i] >= 360: self.rotateAngles[i] -= 360
            if self.rotateAngles[i] < 0: self.rotateAngles[i] += 360

    def setRotationMatrix(self):
        # Set matrix for rotation using angles.
        
        (sx, sy, sz) = np.sin((self.angles + self.rotateAngles) * self.angleScale)
        (cx, cy, cz) = np.cos((self.angles + self.rotateAngles) * self.angleScale)
 
        # build a matrix for X, Y, Z rotation (in that order, see Wikipedia: Euler angles) including position shift. 
        # add a column of zeros for later position use
        self.rotationMatrix = np.array([[cy * cz               , -cy * sz              , sy      ],
                                        [cx * sz + cz * sx * sy, cx * cz - sx * sy * sz, -cy * sx],
                                        [sx * sz - cx * cz * sy, cz * sx + cx * sy * sz, cx * cy ]])
    
class VectorPosition:

    """
    A vector object defining the positions of other objects in its nodes (see VectorObject).
    
    @author: kalle
    """
    def __init__(self):
        self.position = np.array([0.0, 0.0, 0.0, 1.0])
        self.angles = VectorAngles()
        self.nodes = np.zeros((0, 4))                   # nodes will have unrotated X,Y,Z coordinates plus a column of ones for position handling
        self.rotatedNodes = np.zeros((0, 3))            # rotatedNodes will have X,Y,Z coordinates
        self.objects = []                               # connects each node to a respective VectorObject
        self.objName = ""
        
    def addNodes(self, node_array):
        # add nodes (all at once); add a column of ones for using position in transform
        self.nodes = np.hstack((node_array, np.ones((len(node_array), 1))))
        self.rotatedNodes = node_array # initialize with nodes
        
    def addObjects(self, object_list):
        self.objects = object_list

    def rotate(self):
        # apply a rotation defined by a given rotation matrix.
        matrix = np.vstack((self.angles.rotationMatrix, np.zeros((1, 3))))
        # apply rotation and position matrix to nodes
        self.rotatedNodes = np.dot(self.nodes, matrix) + self.position[0:3]
        
        
if __name__ == '__main__':
    """ 
    Prepare screen, read objects etc. from file.
    """

    # set data directory
    os.chdir("E:/development/python/RealTime3DwithPython/Vector3D")

    # set screen size
    # first check available full screen modes
    pygame.display.init()
    # disp_modes = pygame.display.list_modes(0, pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE)
    # disp_size = disp_modes[4] # selecting display size from available list. Assuming the 5th element is nice...
    disp_size = (1280, 800)

    vv = VectorViewer(disp_size[0], disp_size[1])

    # read data file defining angles, movements and objects
    vecdata = et.parse("vectordata ground and roads.xml")

    root = vecdata.getroot()
    
    for angles in root.iter('vectorangles'):
        ang = VectorAngles()
        ang.angName = angles.get('name')
        ang.angles[0] = float(angles.findtext("angleX", default="0"))
        ang.angles[1] = float(angles.findtext("angleY", default="0"))
        ang.angles[2] = float(angles.findtext("angleZ", default="0"))
        vv.addVectorAnglesList(ang)
        # set rotation for viewer angles
        if ang.angName == "viewer":
            vv.viewerAngles = vv.VectorAnglesList[-1]
            vv.viewerAngles.rotate = ([0.0, 0.5, 0.0])
   
    for vecobjs in root.iter('vectorobject'):
        vobj = VectorObject()
        vobj.objName = vecobjs.get('name')
        vobj.prio = int(vecobjs.findtext("prio", default="0"))
        # check if object is the ground. Will be set later.
        ground = None
        ground = vecobjs.get('ground')
            
        # check if object is a copy of another, previously defined object
        copyfrom = None
        copyfrom = vecobjs.get('copyfrom')
        is_copy = False
        if copyfrom is not None:
            for VectorObj in vv.VectorObjs:
                if VectorObj.objName == str(copyfrom):
                    # copy data from another object
                    vobj = copy.deepcopy(VectorObj) # copy properties
                    vobj.angles = VectorObj.angles  # copy reference to angles, does not seem to work with deepcopy()
                    is_copy = True
                    break
                    
        # set position and references to angles and movement
        for posdata in vecobjs.iter('position'):
            vobj.position[0] = float(posdata.findtext("positionX", default="0"))
            vobj.position[1] = float(posdata.findtext("positionY", default="0")) 
            vobj.position[2] = -float(posdata.findtext("positionZ", default="0")) # inverted for easier coordinates definition
        angleName = vecobjs.findtext("anglesref", None)
        for angles in vv.VectorAnglesList:
            if angles.angName == angleName:
                vobj.angles = angles
                break
           
        # get (or set) some default values. Not needed for copied objects.
        if is_copy == True: 
            def_minshade = str(vobj.minShade)
        else: 
            def_minshade = "0.3"
            def_color = (def_colorR, def_colorG, def_colorB) = (128, 128, 128)
            # if not a copied object, read default values for some surface properties
            for def_colordata in vecobjs.iter('defcolor'):
                def_colorR = def_colordata.findtext("defcolorR", default="128")
                def_colorG = def_colordata.findtext("defcolorG", default="128")
                def_colorB = def_colordata.findtext("defcolorB", default="128")
                def_color = (int(def_colorR), int(def_colorG), int(def_colorB))
                break
            def_backColor = (def_backColorR, def_backColorG, def_backColorB) = def_color
            for def_backcolordata in vecobjs.iter('defbackcolor'):
                def_backColorR = def_backcolordata.findtext("defbackcolorR", default=str(def_backColorR))
                def_backColorG = def_backcolordata.findtext("defbackcolorG", default=str(def_backColorG))
                def_backColorB = def_backcolordata.findtext("defbackcolorB", default=str(def_backColorB))
                def_backColor = (int(def_backColorR), int(def_backColorG), int(def_backColorB))
                break
            def_edgeWidth = vecobjs.findtext("defedgewidth", default="0")
            def_showBack = vecobjs.findtext("defshowback", default="0")           
        vobj.minShade = float(vecobjs.findtext("minshade", default=def_minshade))
        
        if is_copy == False:
            # add nodes ie. "points" or "corners". No changes allowed for copied objects.
            for nodedata in vecobjs.iter('nodelist'):
                vobj.nodeNum = int(nodedata.get("numnodes"))
                vobj_nodes = np.zeros((vobj.nodeNum, 3))
                for node in nodedata.iter('node'):
                    node_num = int(node.get("ID"))
                    vobj_nodes[node_num, 0] = float(node.findtext("nodeX", default="0"))
                    vobj_nodes[node_num, 1] = float(node.findtext("nodeY", default="0"))
                    vobj_nodes[node_num, 2] = -float(node.findtext("nodeZ", default="0")) # inverted for easier coordinates definition
                vobj.addNodes(vobj_nodes)
                break # only one nodelist accepted

        # check for initangles ie. initial rotation. Default is none which requires no action.
        for angledata in vecobjs.iter('initangles'):
            angleXadd = float(angledata.findtext("angleXadd", default="0"))
            angleYadd = float(angledata.findtext("angleYadd", default="0"))
            angleZadd = float(angledata.findtext("angleZadd", default="0"))
            if angleXadd != 0 or angleYadd != 0 or angleZadd != 0: 
                storeangles = copy.copy(vobj.angles.angles) # store temporarily
                storeposition = copy.copy(vobj.position) # store temporarily
                vobj.angles.angles = np.array([angleXadd, angleYadd, angleZadd]) # use the requested initial rotation
                vobj.position = np.array([0.0, 0.0, 0.0, 1.0]) # set position temporarily to zero for initial rotation
                vobj.angles.setRotationMatrix()
                vobj.rotate(vobj.angles)
                vobj.nodes = np.hstack((vobj.rotatedNodes, np.ones((np.shape(vobj.rotatedNodes)[0], 1)))) # overwrite original nodes with rotated (to init angles) nodes
                vobj.angles.angles = storeangles
                vobj.position = storeposition
                
        # add surfaces ie. 2D flat polygons. 
        for surfacedata in vecobjs.iter('surfacelist'):
            for surf in surfacedata.iter('surface'):
                idnum = int(surf.get("ID"))
                
                if is_copy == True:
                    for surfobj in vobj.surfaces:
                        if surfobj.idnum == idnum:
                            break
                    def_color = surfobj.color
                    def_backColor = surfobj.backColor
                    def_edgeWidth = str(surfobj.edgeWidth)
                    def_showBack = str(surfobj.showBack)
                    
                color = def_color
                for colordata in surf.iter('color'):
                    colorR = int(colordata.findtext("colorR", default=def_colorR))
                    colorG = int(colordata.findtext("colorG", default=def_colorG))
                    colorB = int(colordata.findtext("colorB", default=def_colorB))
                    color = (colorR, colorG, colorB)
                    break
                backColor = def_backColor
                for backColordata in surf.iter('backColor'):
                    backColorR = int(backColordata.findtext("backColorR", default=def_backColorR))
                    backColorG = int(backColordata.findtext("backColorG", default=def_backColorG))
                    backColorB = int(backColordata.findtext("backColorB", default=def_backColorB))
                    backColor = (backColorR, backColorG, backColorB)
                    break
                edgeWidth = int(surf.findtext("edgewidth", default=def_edgeWidth))
                showBack = int(surf.findtext("showback", default=def_showBack))
                if is_copy == False:
                    # create a list of nodes. No changes allowed for copied objects.
                    node_list = []
                    for nodelist in surf.iter('nodelist'):
                        for node in nodelist.iter('node'):
                            node_order = int(node.get("order"))
                            node_refID = int(node.get("refID"))
                            node_list.append((node_order, node_refID))
                    node_list.sort(key=itemgetter(0)) # sort nodes by node_order
                    node_list = list(zip(*node_list))[1] # pick just the node references
                    vobj.addSurfaces(idnum, color, edgeWidth, showBack, backColor, node_list)
                else:
                    vobj.modifySurfaces(idnum, color, edgeWidth, showBack, backColor)
                            
        # check if is a flat object (one surface only)
        if len(vobj.surfaces) == 1:
            vobj.isFlat = 1
        # add object prio to prio list, if not there
        if not vobj.prio in vv.VectorObjPrios:
            vv.VectorObjPrios.append(vobj.prio)
        # add the object
        vv.addVectorObj(vobj)

        # define this (last added) object as ground if so specified
        if ground is not None:
            vv.groundObject = vv.VectorObjs[-1]
            # precalculate ground colors   
            # add background color for the first component
            vv.groundColors.append(vv.backgroundColor)
            for i in range(vv.groundShadeNr):
                colorShade = ((i / (vv.groundShadeNr - 1)) * vv.groundShades[1] + ((vv.groundShadeNr - 1 - i) / (vv.groundShadeNr - 1)) * vv.groundShades[0]) / 100
                use_color = ([round(colorShade * x, 0) for x in vv.groundObject.surfaces[0].color])
                vv.groundColors.append(use_color)

    # sort prio list
    vv.VectorObjPrios.sort(reverse=True)

    # define a vector position object holding all the positions of other objects in its nodes
    for vecobjs in root.iter('positionobject'):
        vobj = VectorPosition()                   
        vobj.objName = vecobjs.get('name')
        for posdata in vecobjs.iter('position'):
            vobj.position[0] = float(posdata.findtext("positionX", default="0"))
            vobj.position[1] = float(posdata.findtext("positionY", default="0"))
            vobj.position[2] = float(posdata.findtext("positionZ", default="1500"))
        angleName = vecobjs.findtext("anglesref", None)
        for angles in vv.VectorAnglesList:
            if angles.angName == angleName:
                vobj.angles = angles
                break
        # get nodes from existing objects
        vobj_nodes = np.zeros((0, 3))
        object_num = 0
        object_list = []
        for VectorObj in vv.VectorObjs:
            vobj_nodes = np.vstack((vobj_nodes, VectorObj.position[0:3]))
            object_list.append((object_num, VectorObj))  # reference to object position data row and respective object
            object_num += 1
        vobj.addNodes(vobj_nodes)
        vobj.addObjects(object_list)           
        # set the object
        vv.setVectorPos(vobj)
        break
    
    # run the main program
    vv.run()
