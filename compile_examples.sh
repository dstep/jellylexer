#!/bin/sh

CC="g++"
EXT=".exe"

for D in examples/*; do
    if [ -d "${D}" ]; then
        echo "Processing ${D}"
		echo "======================"
		
		for F in ${D}/*.jlex; do
			python3 -m jellylexer.run --dir ${D} -vv ${F}
		done
		
		mkdir -p .build/examples
		
		${CC} -O2 "${D}/"*.cpp -o ".build/${D}${EXT}"
		
		HAD_FILE=0
		for F in ${D}/*.input; do
			if [ -e "${F}" ]; then
				echo " *** Running for ${F} *** "
				".build/${D}${EXT}" "${F}"
				HAD_FILE=1
			fi
		done
		
		if [ "${HAD_FILE}" -eq "0" ]; then
			echo " *** Running lexer *** "
			".build/${D}${EXT}"
		fi
		
		echo;
		echo;
    fi
done


