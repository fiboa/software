from os import error
from pathlib import Path
from datetime import datetime
from jinja2 import Template
import logging
import requests
import os
import sys
import yaml

logger = logging.getLogger(__name__)

headers = {}
env = dict(os.environ)
if "GITHUB_TOKEN" in env:
  headers["Authorization"] = " ".join(["Bearer", os.environ["GITHUB_TOKEN"]])
else:
  logger.warn("No GITHUB_TOKEN found in env")

config = yaml.safe_load(Path("./config.yaml").read_text())

def unslugify(s: str) -> str:
  return s.replace("-", " ").replace("_", " ").title()

def from_gh(response) -> dict:
  topics = response["topics"].copy()
  if "software" in topics:
    topics.remove("software")
  if "tooling" in topics:
    topics.remove("tooling")
  data = {
    "title": unslugify(response["name"]),
    "url": response["html_url"],
    "description": response["description"],
    "topics": topics
  }
  if response["archived"]:
    data["description"] = "**DEPRECATED.** " + data["description"]
  return data

def get_software() -> list:
  data = []

  try:
    logger.info(f"Reading list of repositories")
    with requests.get("https://api.github.com/users/fiboa/repos?per_page=1000", headers=headers) as site:
      repos = site.json()
      for repo in repos:
        if not isinstance(repo, dict):
          logger.error(f"response invalid")
          continue
        if repo["is_template"] or repo["visibility"] !=	"public" or ("software" not in repo["topics"] and "tooling" not in repo["topics"]):
          continue
        data.append(from_gh(repo))
  except error as e:
      logger.error(f"fiboa org not available: {e}")

  for r in config["github"]:
    try:
      logger.info(f"Reading community GitHub repos individually")
      with requests.get(f"https://api.github.com/repos/{r['org']}/{r['repo']}", headers=headers) as repo:
        data.append(from_gh(repo.json()))
    except error as e:
        logger.error(f"community repo not available: {e}")

  for r in config["external"]:
    data.append(r)

  return data

def main() -> bool:
  data = get_software()
  data.sort(key = lambda x: x["title"])
  count = len(data)
  now = datetime.utcnow().strftime("%b %d %Y, %H:%M %Z")
  template = Template(Path("./README.md.jinja").read_text())

  with Path("./README.md") as f:
    f.write_text(template.render(software=data, updated=now, count=count))

  sys.exit(0)


if __name__ == "__main__":
  main()
