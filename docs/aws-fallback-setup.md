# AegisOS — AWS EC2 Fallback Setup (Phase 8+)

Use this guide **only when you reach Phase 8** (kdump & kernel crash analysis). Your WSL environment handles Phases 1–7 and 10.

---

## When You Need AWS

- Configuring and testing **kdump** crash dump capture
- Analyzing **vmcore** files with the `crash` utility
- Optional **Livepatch/kpatch** demonstration (Phase 9)

Estimated usage: **2–4 hours** of instance runtime across Phase 8–9.

---

## Step 1 — Launch an EC2 Instance

1. Sign in to [AWS Console](https://console.aws.amazon.com/ec2/)
2. **Launch instance**
   - **Name:** `aegisos-kdump-lab`
   - **AMI:** Ubuntu Server 24.04 LTS (64-bit x86)
   - **Instance type:** `t3.micro` (Free Tier eligible) or `t3.small`
   - **Key pair:** Create or select an existing `.pem` key
   - **Storage:** 20 GB gp3 (default is fine)
   - **Security group:** Allow SSH (port 22) from your IP only
3. Launch and note the **public IP**

---

## Step 2 — Connect via SSH

From PowerShell or WSL:

```bash
ssh -i /path/to/your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

---

## Step 3 — Install AegisOS Dependencies

On the EC2 instance:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git build-essential kdump-tools crash
```

Clone or copy your project:

```bash
git clone <your-repo-url> Self-Healing-OS
cd Self-Healing-OS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Step 4 — Configure kdump

```bash
sudo apt-get install -y kdump-tools
sudo kdump-config show
```

Edit `/etc/default/grub.d/kdump-tools.cfg` if needed, then:

```bash
sudo kdump-config load
```

**Warning:** Triggering a kernel panic (`echo c > /proc/sysrq-trigger`) will crash the instance. Only do this on a disposable lab instance with no important data.

---

## Step 5 — Sync Code Between WSL and EC2

**Option A — Git (recommended):**

```bash
# On WSL (Windows side)
git push origin main

# On EC2
git pull origin main
```

**Option B — SCP:**

```powershell
scp -i key.pem -r "D:\VIT\Sem 5\Operating System\Self-Healing-OS\kdump" ubuntu@<IP>:~/Self-Healing-OS/
```

---

## Step 6 — Tear Down

When Phase 8–9 labs are complete:

1. Export any vmcore samples or lab notes you need
2. **Stop** or **Terminate** the EC2 instance to avoid charges
3. Continue Phases 9–10 integration work on WSL

---

## Cost Estimate

| Resource | Approximate cost |
|----------|------------------|
| t3.micro (Free Tier, 750 hrs/mo first year) | $0 |
| t3.micro (after Free Tier) | ~$0.01/hr |
| 20 GB EBS storage | ~$2/month if left running |

**Always stop/terminate the instance when not in use.**

---

## Architecture Split

```text
Development (Phases 1–7, 10)     Phase 8–9 labs only
         │                                │
         ▼                                ▼
    WSL2 Ubuntu                   AWS EC2 Ubuntu
    (daily driver)                (kdump / kernel)
```

Both environments run the same Python codebase; only the kernel-level features differ.
