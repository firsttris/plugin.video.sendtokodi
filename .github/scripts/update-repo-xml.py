#!/bin/python3

import os
import argparse
import xml.etree.ElementTree as ET

# check and parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("--repo-root", required=True)
args = parser.parse_args()

# get the addon's XML element
src_filename = "addon.xml"
src_tree = ET.parse(src_filename)
src_element = src_tree.getroot()

# instantiate the repo's XML template
tpl_filename = os.path.join(args.repo_root, "addon.template.xml")
tpl_tree = ET.parse(tpl_filename)
tpl_element = tpl_tree.getroot()
tpl_element.append(src_element)

# write changes to the repo's addon.xml file
dst_filename = os.path.join(args.repo_root, "addon.xml")
tpl_tree.write(dst_filename, encoding='UTF-8', xml_declaration=True)  
