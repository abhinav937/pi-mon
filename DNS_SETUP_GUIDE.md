# DNS Setup Guide for pi.cabhinav.com

This guide will help you set up DNS records to make your Pi Monitor application accessible at `pi.cabhinav.com`.

## Prerequisites

- Access to your domain registrar's DNS management panel
- Your server's public IP address
- Domain: `cabhinav.com`

## Step 1: Your Static IP Address

**Your Pi has a static IP address: `65.36.123.68`**

This is the IP address you'll use for your DNS records. No need to check for dynamic IP changes.

## Step 2: Add DNS Records

Log into your domain registrar's DNS management panel and add the following records:

### Option A: A Record (Recommended)

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | pi | YOUR_SERVER_IP | 300 (or default) |

**Example:**
- **Type:** A
- **Name:** pi
- **Value:** 65.36.123.68 (your Pi's static IP)
- **TTL:** 300 seconds (5 minutes)

### Option B: CNAME Record (Alternative)

If you prefer using a CNAME record:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| CNAME | pi | YOUR_SERVER_IP | 300 (or default) |

**Note:** CNAME records are not recommended for root domains, but work fine for subdomains.

## Step 3: Verify DNS Propagation

After adding the DNS record, it may take some time to propagate. You can check the status using:

```bash
# Check if the domain resolves
nslookup pi.cabhinav.com

# Or use dig (more detailed)
dig pi.cabhinav.com

# Or use online tools
# Visit: https://www.whatsmydns.net/
# Enter: pi.cabhinav.com
```

## Step 4: Test the Connection

Once DNS propagation is complete, test your setup:

```bash
# Test HTTP connection
curl -I http://pi.cabhinav.com

# Test HTTPS connection (after SSL setup)
curl -I https://pi.cabhinav.com

# Test API endpoint
curl https://pi.cabhinav.com/health
```

## Common DNS Providers

### Cloudflare
1. Go to your domain dashboard
2. Click on "DNS" in the left sidebar
3. Click "Add record"
4. Select "A" record type
5. Name: `pi`
6. IPv4 address: `YOUR_SERVER_IP`
7. TTL: `Auto` or `300`
8. Click "Save"

### GoDaddy
1. Go to your domain management page
2. Click "DNS" tab
3. Click "Add" under "DNS Records"
4. Type: `A`
5. Host: `pi`
6. Points to: `YOUR_SERVER_IP`
7. TTL: `1 Hour`
8. Click "Save"

### Namecheap
1. Go to "Domain List" → click "Manage"
2. Click "Advanced DNS" tab
3. Click "Add New Record"
4. Type: `A Record`
5. Host: `pi`
6. Value: `YOUR_SERVER_IP`
7. TTL: `5 min`
8. Click "Save Changes"

### Google Domains
1. Go to your domain management page
2. Click "DNS" tab
3. Click "Create new record"
4. Type: `A`
5. Name: `pi`
6. Data: `YOUR_SERVER_IP`
7. TTL: `300`
8. Click "Create"

## Troubleshooting

### DNS Not Resolving
- Wait longer for propagation (can take up to 48 hours)
- Check if the DNS record was saved correctly
- Verify the IP address is correct
- Try using different DNS servers (8.8.8.8, 1.1.1.1)

### Wrong IP Address
- Make sure you're using the public IP, not local IP
- If you're behind NAT, use your router's public IP
- Consider using a dynamic DNS service if your IP changes frequently

### Subdomain Not Working
- Ensure the A record name is exactly `pi` (not `pi.cabhinav.com`)
- Check that your server is listening on ports 80 and 443
- Verify firewall settings allow incoming connections

## Dynamic DNS (Optional)

If your server's IP address changes frequently, consider using a dynamic DNS service:

1. **No-IP**: Free dynamic DNS service
2. **DuckDNS**: Free dynamic DNS service
3. **Cloudflare**: Update DNS records via API

## Security Considerations

- Only expose necessary ports (80, 443)
- Use strong SSL certificates
- Keep your server updated
- Monitor access logs regularly

## Next Steps

After DNS setup is complete:

1. **Deploy your application** using the provided scripts
2. **Set up SSL certificates** using Let's Encrypt
3. **Test the application** at https://pi.cabhinav.com
4. **Monitor logs** for any issues

## Support

If you encounter issues:

1. Check the DNS propagation status
2. Verify your server configuration
3. Check application logs
4. Ensure ports are open and accessible

---

**Remember:** DNS changes can take time to propagate globally. Be patient and test from different locations if possible.
