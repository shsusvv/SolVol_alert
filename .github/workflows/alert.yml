name: sol-volume-alert
on:
  schedule:
    - cron: "*/30 * * * *"
  workflow_dispatch:
permissions:
  contents: write
jobs:
  check:
    runs-on: ubuntu-latest
    env:
      TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install requests
      - name: Test message (manual runs only)
        if: github.event_name == 'workflow_dispatch'
        run: python sol_volume_alert.py --test
      - run: python sol_volume_alert.py
      - name: Save state
        run: |
          git config user.name "bot"
          git config user.email "bot@users.noreply.github.com"
          git add state.json
          git diff --staged --quiet || (git commit -m "state" && git push)
