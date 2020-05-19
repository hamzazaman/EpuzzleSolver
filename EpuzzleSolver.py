#!/usr/bin/env python
# coding: utf-8

import requests
import random
import queue
import numpy as np
from splinter import Browser
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
from sklearn.metrics import mean_squared_error
from skimage import measure
from io import BytesIO



puzzle = 'http://www.epuzzle.info/newboard.php?n=b931'
username = 'botThatWillBeBanned'
country = None
ssim = False
solveOrder = 'sorted'
start = 'edge'
useSlave = False


def imgDifScore(im1, im2, ssim=False):
    # Measure the difference between images and assign a score. Lower is more similar
    # Can use MSE or SSIM
    im1 = np.array(im1)
    im2 = np.array(im2)
    if ssim:
        scores = [-1*measure.compare_ssim(im1[:, :, i], im2[:, :, i]) for i in range(3)]
    else:
        scores = [mean_squared_error(im1[:, :, i], im2[:, :, i]) for i in range(3)]
    return sum(scores)


browser = Browser()
if useSlave:
    slave = Browser()

browser.driver.implicitly_wait(30)
browser.visit(puzzle)
browser.find_by_id('ss').click()
browser.find_by_css('option[value="2"]').click()
browser.find_by_css('a[class="auloz"]').click()

mini = browser.find_by_css('img[class="dminiatura"]').first
src = mini['src']
src = src.replace('mini_', '')
response = requests.get(src)
source = Image.open(BytesIO(response.content))

shareable = browser.find_by_id('gaurl')['href']
browser.find_by_id('gaurl').click()

browser.find_by_css('a[class="auloz"]').click()

parent_window = browser.driver.current_window_handle
all_windows = browser.driver.window_handles
child_window = [window for window in all_windows if window != parent_window][0]
browser.driver.switch_to.window(child_window)

browser.fill('osoba', username)
if country:
    browser.select("pkraj", country)
browser.find_by_id('submit').click()

try:
    WebDriverWait(browser.driver, 10).until(
        EC.presence_of_element_located(('id', "sb"))
    )
    element = WebDriverWait(browser.driver, 10).until(
        EC.element_to_be_clickable(('id', "sb"))
    )
    element.click()
    browser.execute_script('return document.getElementById("stats").remove();')
finally:
    pass

if useSlave:
    slave.visit(shareable)
    slave.find_by_css('a[class="auloz"]').click()

    parent_window = slave.driver.current_window_handle
    all_windows = slave.driver.window_handles
    child_window = [window for window in all_windows if window != parent_window][0]
    slave.driver.close()
    slave.driver.switch_to.window(child_window)

    slave.fill('osoba', username + "Helper")
    if country:
        slave.select("pkraj", country)
    slave.find_by_id('submit').click()
    slave.execute_script('return document.getElementById("stats").remove();')


elements = browser.driver.find_elements_by_tag_name('canvas')
if useSlave:
    slaveElements = slave.find_by_tag('canvas')
i = 0
xvals = np.array([])
yvals = np.array([])
images = []

for selEl in elements:
    location = selEl.location
    size = selEl.size
    im = Image.open(BytesIO(selEl.screenshot_as_png))
    images += [im]
    xvals = np.append(xvals, location['x']) 
    yvals = np.append(yvals, location['y']) 
    i += 1
    
totalLength = i
pieceWidth = images[0].getbbox()[-2]
pieceHeight = images[0].getbbox()[-1]
xvals = np.unique(xvals)
yvals = np.unique(yvals)
dim = (len(xvals), len(yvals))

source = source.resize((pieceWidth*dim[0], pieceHeight*dim[1]))
sourceWidth = source.getbbox()[-2]
sourceHeight = source.getbbox()[-1]

cursorElem = browser.driver.find_element_by_xpath("//div[@id='play']/div[1]")

i = 0
imgObjects = []
imgObjects1dCpy = []
imgObjects1d = []
sourceImages = []
allIndex = []
for y in range(dim[1]):
    imsl = []
    sisl = []
    for x in range(dim[0]):
        allIndex.append((y, x))
        im = images[i]
        obj = {"im": im, "elem": elements[i], "dest": (-1, -1)}
        if useSlave:
            obj['slave'] = slaveElements[i]
        imsl.append(None)
        imgObjects1dCpy.append(obj)
        imgObjects1d.append(obj)
        sourceIm = source.crop((x*pieceWidth, y*pieceHeight, (x+1)*pieceWidth, (y+1)*pieceHeight))
        sisl.append(sourceIm)
        i += 1
    imgObjects.append(imsl)
    sourceImages.append(sisl)


pixHeight = yvals[1] - yvals[0]
pixWidth = xvals[1] - xvals[0]
miny = min(yvals)
minx = min(xvals)
misplaced = []

def getObjLoc(obj):
    loc = obj['elem'].location
    x = loc['x'] - minx
    y = loc['y'] - miny
    return (int(round(y/pixHeight)), int(round(x/pixWidth)))

def resortObjs(q = None):
    print("Resorting Objects")
    imgObjects1dCpy.clear()
    for obj in imgObjects1d:
        y, x = getObjLoc(obj)
        imgObjects[y][x] = obj
        if obj['dest'] != (y,x):
            imgObjects1dCpy.append(obj)
            if q != None:
                q.put((y,x))
            
def getObjFromLoc(y, x, q = None):
    cur = imgObjects[y][x]
    if getObjLoc(cur) == (y, x):
        return cur
    else:
        resortObjs(q)
        return getObjFromLoc(y, x)

def sortKey(obj):
    xDistFromMid = abs(obj[1] - dim[0]/2.0 + 0.5)
    yDistFromMid = abs(obj[0] - dim[1]/2.0 + 0.5)
    if start == 'middle':
        return max(yDistFromMid, xDistFromMid)
    elif start == "corner":
        return (obj[0]) + (obj[1])
    elif start == 'edge':
        return -max(yDistFromMid, xDistFromMid)


resortObjs()

if solveOrder == "random":
    random.shuffle(allIndex)
elif solveOrder == "sorted":
    if start != "top":
        allIndex.sort(key=sortKey)

q = queue.Queue()
for a in allIndex:
    q.put(a)

while not q.empty():
    t = q.get()
    sy = t[0]
    sx = t[1]
    sourceIm = sourceImages[sy][sx]
    minscore = float("inf")
    winObj = None

    try:
        target = getObjFromLoc(sy, sx, q = q)
    except Exception:
        print("Tried Getting Target and failed")
        break

    try:
        target['elem'].click()
    except Exception:
        if cursorElem.location['x'] >= 0:
            cursorElem.click()
        target['elem'].click()

    i = 0
    for curImg in imgObjects1dCpy:
        i += 1
        if curImg != None:
            score = imgDifScore(sourceIm, curImg['im'], ssim)
            if score < minscore:
                minscore = score
                curImg['dest'] = (sy, sx)
                winObj = curImg
        
    if winObj == None: # Puzzle Must be done
        break
    dest = winObj['dest']
    try:
        loc = getObjLoc(winObj)
    except Exception:
        print("Tried Getting Loc and failed")
        break
    if loc != dest:
        winObj['elem'].click()
        imgObjects[dest[0]][dest[1]] = winObj
        imgObjects[loc[0]][loc[1]] = target
        target['loc'] = loc
        winObj['loc'] = dest
    else:
        try:
            cursorElem.click()
        except Exception:
            pass
        
    imgObjects1dCpy.remove(winObj)





