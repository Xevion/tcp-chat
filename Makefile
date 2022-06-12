.DEFAULT_GOAL := build
.PHONY: build test clean clean-spec run-server run-client

run-server:
	python launch.py s

run-client:
	python launch.py c

build:
	pyinstaller --onefile launch.py -n tcp-chat --clean

clean:
	rm ./build/ -r
	rm ./dist/ -r

clean-spec:
	rm *.spec
