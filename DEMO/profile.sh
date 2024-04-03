#!/bin/bash

# Monitoring duration and interval
DURATION=10 # 60 seconds
INTERVAL=1 # 1-second intervals
XGEN=$1

# File names for data collection
CPU_FILE="${XGEN}-cpu_usage.dat"
MEM_FILE="${XGEN}-memory_usage.dat"
RST_FILE="${XGEN}-tcp-rst.dat"
SYN_FILE="${XGEN}-tcp-syn.dat"
CPU_PLOT_FILE="${XGEN}-performance_plots.plt"
NET_PLOT_FILE="${XGEN}-network.plt"
INTERFACE="eno1"
sudo echo
# Start monitoring CPU and memory, outputting to files
sar -u $INTERVAL $DURATION > $CPU_FILE &
sar -r $INTERVAL $DURATION > $MEM_FILE &

# Capture TCP SYN and RST packets, process the output, and save it in a GNU Plot compatible format
timeout $DURATION sudo tcpdump -i "$INTERFACE" 'tcp[tcpflags] & (tcp-rst) != 0' -tt -n -l | awk '{ print $1, $3 }' | sed -r 's/:[^:]+$//' > "$RST_FILE" &
timeout $DURATION sudo tcpdump -i "$INTERFACE" 'tcp[tcpflags] & (tcp-syn) != 0' -tt -n -l | awk '{ print $1, $3 }' | sed -r 's/:[^:]+$//' > "$SYN_FILE" &

python3 "$2" "${@:3}"

wait # Wait for the above processes to finish

# Assuming data processing scripts are prepared to convert sar and tcpdump outputs to a gnuplot-friendly format

cat > $CPU_PLOT_FILE <<EOL
set terminal png
set output cpu.png
set title 'CPU Usage Over Time'
set xlabel 'Time (s)'
set ylabel 'CPU Usage (%)'
plot '$CPU_FILE' using 1:3 with lines title 'CPU Usage'
EOL

gnuplot $CPU_PLOT_FILE

cat > $NET_PLOT_FILE <<EOL
set terminal png
set output network.png
set title "TCP SYN vs RST Packets Over Time"
set xlabel "Time (s)"
set ylabel "Packet Count"
plot "$SYN_FILE" using 1:2 with linespoints title 'SYN', \
     "$RST_FILE" using 1:2 with linespoints title 'RST'
EOL

gnuplot $NET_PLOT_FILE


# Repeat the above gnuplot script for memory usage and network traffic, adjusting the 'plot' line accordingly.
