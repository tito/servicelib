.PHONY: all build

all:
	rm *.apk || true
	P4A_kivy_DIR=/home/tito/code/kivy p4a apk --debug --android_api 19 --arch armeabi-v7a --dist_name testservices --bootstrap=sdl2 --requirements=python2,kivy==master,pyzmq --private /home/tito/code/testservices --version 1 --package org.kivy.testservices --copy-libs --name _PAUSE --permission INTERNET --service s1:service_1.py --service s2:service_2.py --service s3:service_3.py
	adb install -r _PAUSE-1-debug.apk
	adb shell am start -n org.kivy.testservices/org.kivy.android.PythonActivity -a org.kivy.android.PythonActivity

build:
	# p4a clean_recipe_build kivy
	p4a clean_dists
	env P4A_kivy_DIR=/home/tito/code/kivy p4a create --debug --android_api 19 --arch armeabi-v7a --dist_name testservices --bootstrap=sdl2 --requirements=python2,kivy==master,pyzmq --copy-libs
