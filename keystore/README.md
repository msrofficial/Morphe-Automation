# Keystore
CI generates `keystore/unified.jks` on first build if missing:
keytool -genkeypair -keystore keystore/unified.jks -alias morphe -keyalg RSA -keysize 2048 -validity 10950 -storepass morphe -keypass morphe -dname "CN=Morphe-Automation"
All APKs and modules use this single key. Changing it later forces clean reinstall.
