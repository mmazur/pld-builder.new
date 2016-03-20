PACKAGE		:= pld-builder
VERSION		:= 0.6
SNAP		:= $(shell date +%Y%m%d)

all: compile

compile:
	python -c "import compileall; compileall.compile_dir('.')"

clean:
	find -name '*.pyc' | xargs rm -f
	rm -f *.tar.bz2

dist: $(PACKAGE)-$(VERSION).$(SNAP).tar.bz2
	test ! -x ./dropin || ./dropin $<

%.tar.bz2: %.tar
	bzip2 -9 $<

%.tar:
	git archive --prefix=$(patsubst %.tar,%,$@)/ HEAD -o $@
