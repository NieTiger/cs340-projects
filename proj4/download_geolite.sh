#!/bin/bash
wget https://networks.cs.northwestern.edu/CS340-w21/project/project%204%20inputs/GeoLite2-City_20201103.tar.gz
tar xvf GeoLite2-City_20201103.tar.gz
mv ./GeoLite2-City_20201103/GeoLite2-City.mmdb .
rm -rf ./GeoLite2-City_20201103/ ./GeoLite2-City_20201103.tar.gz

