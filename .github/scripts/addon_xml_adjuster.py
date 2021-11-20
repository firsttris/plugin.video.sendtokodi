#!/bin/python3
# bash provides not builtin xml editor.
# sed can be error-prone in case of minor ajustments to the original xml file
# xmlstarlet etc. would need to be installed in the ci first
# python including the xml module is available on almost any server   
import xml.etree.ElementTree as ET
import argparse

# check and parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("--plugin-version", required=True)
parser.add_argument("--xbmc-python", required=True)
args = parser.parse_args()

# read thaeaddon.xml
filename = "addon.xml"
xml_tree = ET.parse(filename)
# get addon element and change the version of the plugin
addon_element = xml_tree.getroot()
addon_element.set("version",args.plugin_version)
# change the xbmc.python for the correct kodi version
for node in addon_element.findall('.//import'):
    if node.attrib['addon']=="xbmc.python":
        node.attrib['version'] = args.xbmc_python
# write the changed xml to the addon.xml file      
xml_tree.write(filename,encoding='UTF-8',xml_declaration=True)  