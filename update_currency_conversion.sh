cd "src/currency"

rm -f eurofxref*

wget 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip'
wget 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref.zip'
unzip 'eurofxref.zip' && rm 'eurofxref.zip'