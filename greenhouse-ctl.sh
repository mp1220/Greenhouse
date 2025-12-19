#!/bin/bash
# Greenhouse Gateway Service Control Script

case "$1" in
  start)
    sudo systemctl start greenhouse-gateway
    echo "Starting greenhouse-gateway service..."
    sleep 1
    sudo systemctl status greenhouse-gateway --no-pager
    ;;
  stop)
    sudo systemctl stop greenhouse-gateway
    echo "Stopping greenhouse-gateway service..."
    ;;
  restart)
    sudo systemctl restart greenhouse-gateway
    echo "Restarting greenhouse-gateway service..."
    sleep 1
    sudo systemctl status greenhouse-gateway --no-pager
    ;;
  status)
    sudo systemctl status greenhouse-gateway
    ;;
  logs)
    sudo journalctl -u greenhouse-gateway -f
    ;;
  recent)
    sudo journalctl -u greenhouse-gateway -n 100 --no-pager
    ;;
  enable)
    sudo systemctl enable greenhouse-gateway
    echo "greenhouse-gateway service enabled (will start on boot)"
    ;;
  disable)
    sudo systemctl disable greenhouse-gateway
    echo "greenhouse-gateway service disabled (will not start on boot)"
    ;;
  *)
    echo "Greenhouse Gateway Service Control"
    echo ""
    echo "Usage: $0 {start|stop|restart|status|logs|recent|enable|disable}"
    echo ""
    echo "Commands:"
    echo "  start   - Start the service"
    echo "  stop    - Stop the service"
    echo "  restart - Restart the service"
    echo "  status  - Show service status"
    echo "  logs    - Follow live logs (Ctrl+C to exit)"
    echo "  recent  - Show last 100 log lines"
    echo "  enable  - Enable auto-start on boot"
    echo "  disable - Disable auto-start on boot"
    exit 1
    ;;
esac
