#!/bin/bash

rm -rf _build/html/
rm -rf _build/markdown/
rm -rf _build/doctrees/

make markdown
make html

rm -rf ../docs_html/
rm -rf ../docs_markdown/

cp -rf _build/html/ ../docs_html/
cp -rf _build/markdown/ ../docs_markdown/
cp -rf _build/doctrees/ ../doctrees/

# patch
#cp -rf source/_static ../docs_markdown/_static
