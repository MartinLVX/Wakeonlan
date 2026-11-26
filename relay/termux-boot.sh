#!/data/data/com.termux/files/usr/bin/sh
# Arranca el relay al encender el Android. Requiere la app Termux:Boot.
# Instalar:  mkdir -p ~/.termux/boot && cp termux-boot.sh ~/.termux/boot/wol-relay && chmod +x ~/.termux/boot/wol-relay
termux-wake-lock
cd "$HOME/Wakeonlan/relay" || exit 1
# Si el relay se cae, vuelve a arrancar a los 5 segundos.
while true; do
  python wol_relay.py >> "$HOME/wol-relay.log" 2>&1
  sleep 5
done
