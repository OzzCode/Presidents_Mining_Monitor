# Miner Reboot Configuration

## Overview

The reboot functionality has been updated to use the miner's web interface instead of the CGMiner API. This ensures a **full hardware reboot** rather than just restarting the mining software.

## How It Works

The system now:
1. Attempts to reboot miners via their HTTP web interface using standard CGI endpoints
2. Tries multiple authentication methods (Digest Auth and Basic Auth)
3. Tests multiple common endpoints for different firmware versions
4. Falls back to CGMiner API if web interface is unavailable

## Configuration

### Setting Miner Credentials

You can configure your miner's web interface credentials in two ways:

#### Option 1: Environment Variables (Recommended)

Add these to your `.env` file:

```env
MINER_USERNAME=root
MINER_PASSWORD=your_password_here
```

#### Option 2: Default Credentials

If not configured, the system will try these common default credentials:
- `root` / `root` (most common)
- `admin` / `admin`
- `root` / `admin`

### Supported Endpoints

The system automatically tries these endpoints:
- `/cgi-bin/reboot.cgi` - Standard Antminer endpoint
- `/cgi-bin/restart.cgi` - Alternative endpoint
- `/api/reboot` - Custom firmware endpoint

## Testing the Reboot Function

1. Navigate to the Remote Management page in the web interface
2. Select a miner and click the "Reboot" button
3. The miner should perform a full hardware reboot
4. Check the command history to see the status

## Troubleshooting

### Miner Not Rebooting

**Check Credentials:**
- Verify your miner's web interface credentials
- Try logging into the miner's web interface manually at `http://[miner-ip]`
- Update the credentials in your `.env` file

**Check Firmware:**
- Some custom firmwares may use different endpoints
- Check your miner's documentation for the correct reboot endpoint

**Check Network:**
- Ensure the monitoring system can reach the miner's web interface (port 80)
- Test with: `curl http://[miner-ip]/cgi-bin/reboot.cgi -u root:root --digest`

### Authentication Errors

If you see authentication errors in the logs:
1. Confirm the correct username/password for your miners
2. Try accessing the miner's web interface manually
3. Update `MINER_USERNAME` and `MINER_PASSWORD` in your `.env` file

### Connection Timeouts

Connection timeouts after sending the reboot command are **normal** and expected - they indicate the miner is restarting.

## Security Notes

- Store credentials in the `.env` file (not committed to version control)
- Use strong passwords for your miners
- Consider network segmentation for your mining infrastructure
- The system uses both Digest Auth (more secure) and Basic Auth (fallback)

## Technical Details

### Previous Behavior
- Used CGMiner API `restart` command
- Only restarted mining software, not hardware
- Miners appeared to accept the command but didn't actually reboot

### Current Behavior
- Uses HTTP requests to miner's web interface
- Performs full hardware reboot
- Tries multiple authentication methods and endpoints
- Falls back to CGMiner API if web interface fails

### Response Handling
- **200 OK**: Reboot command successfully sent
- **401/403**: Authentication issue, tries alternative methods
- **Timeout**: Expected behavior, miner is rebooting
- **Connection Error**: Expected behavior, miner is restarting

## Example Configuration

Create or update your `.env` file:

```env
# Miner Web Interface Credentials
MINER_USERNAME=root
MINER_PASSWORD=MySecurePassword123

# Other settings...
MINER_IP_RANGE=192.168.1.0/24
POLL_INTERVAL=30
```

## Support

If you continue to experience issues:
1. Check the application logs in the `logs/` directory
2. Review the command history in the Remote Management page
3. Verify your miner's firmware version and documentation
4. Test the reboot endpoint manually using curl or a web browser
