.DEFAULT_GOAL := build
.PHONY: build test cert clean clean-spec run-server run-client

run-server:
	python launch.py s

run-client:
	python launch.py c

test:
	pytest

cert:
	openssl req -x509 -newkey rsa:2048 -nodes -keyout shared/key.pem -out shared/cert.pem -days 365 -subj /CN=localhost

build:
	pyinstaller --onefile launch.py -n tcp-chat --clean

clean:
	rm ./build/ -r
	rm ./dist/ -r

clean-spec:
	rm *.spec
