LLVM ?= /opt/homebrew/opt/llvm
CXX := $(LLVM)/bin/clang++
CXXFLAGS := $(shell $(LLVM)/bin/llvm-config --cxxflags) -fPIC -O2
LDFLAGS := $(shell $(LLVM)/bin/llvm-config --ldflags) -shared -undefined dynamic_lookup

build/IRFeatures.dylib: plugin/IRFeatures.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDFLAGS)

.PHONY: plugin test
plugin: build/IRFeatures.dylib
test:
	.venv/bin/python -m pytest -q
