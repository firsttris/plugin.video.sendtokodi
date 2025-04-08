#!/bin/python3
import xml.etree.ElementTree as ET
import argparse

# check and parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("--plugin-version", required=True)
args = parser.parse_args()

# read the addon.xml file
filename = "addon.xml"
xml_tree = ET.parse(filename)
# get the addon element and change the version of the plugin
addon_element = xml_tree.getroot()
addon_element.set("version",args.plugin_version)
# write changes to the addon.xml file      
xml_tree.write(filename,encoding='UTF-8',xml_declaration=True)  
