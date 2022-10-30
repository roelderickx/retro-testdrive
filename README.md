# Test Drive

This repository contains a proof of concept to extract the sprites of the Test Drive game by Distinctive Software, released by Accolade in 1987. Information on the original game can be found on [wikipedia](https://en.wikipedia.org/wiki/Test_Drive_(1987_video_game)).

# Proof of concept

An installation of python 3 is required to run the proof of concept. Create a subdirectory called `testdrive` and put the original game in this directory before running `extract-sprites.py`. All sprites from all CMP (4 colors CGA) files in the testdrive directory will be unpacked to a new directory called `sprites`.
The PES files (16 colors EGA) have a different compression mechanism which is to be investigated.

# To do

Add documentation of the file format.

