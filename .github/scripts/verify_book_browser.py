#!/usr/bin/env python3
"""Verify downloads, page navigation, redirects, and optional saved widgets."""

import argparse
import re
from playwright.sync_api import expect, sync_playwright


def verify(url: str, executable: str | None, widgets: bool, screenshot: str | None) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, args=["--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.request.get(url + "/neurodesk-pages.json")
        assert response.ok, "Missing page inventory"
        routes = response.json()
        source = "examples/structural_imaging/brain_extraction_different_tools.ipynb"
        notebook_url = url + "/" + routes[source]
        page.goto(notebook_url, wait_until="domcontentloaded")
        expect(page.locator(".nd-launch")).to_have_count(1)
        page.get_by_text("Run this notebook", exact=True).click()
        launches = page.locator('.nd-launch a[href*="/hub/user-redirect/git-pull?"]')
        expect(launches).to_have_count(5)
        for launch in launches.all():
            expect(launch).to_be_visible()

        page.get_by_role("button", name="Downloads").click()
        download = page.get_by_role("link", name="Download Download source notebook")
        expect(download).to_be_visible()
        raw_url = url + "/_sources/" + source
        assert download.evaluate("el => el.href") == raw_url, "Download menu points to the wrong source"
        fetched = page.request.get(raw_url)
        assert fetched.ok, "Raw download failed"
        raw = fetched.json()
        assert "nd-launch" not in str(raw), "Download includes generated controls"
        page.keyboard.press("Escape")

        page.get_by_role("link", name=re.compile("^Structural imaging$", re.IGNORECASE)).click()
        expect(page.locator(".nd-launch")).to_have_count(0)
        expect(page.locator(".nd-review-badge")).to_have_count(0)
        page.go_back(wait_until="domcontentloaded")
        expect(page.locator(".nd-launch")).to_have_count(1)

        if widgets:
            frames = page.locator('iframe[title="Interactive notebook output"]')
            expect(frames).to_have_count(5)
            for frame in frames.all():
                frame.scroll_into_view_if_needed()
                expect(frame.content_frame.locator("canvas")).to_be_visible(timeout=60000)
            frames.first.scroll_into_view_if_needed()
        if screenshot:
            page.screenshot(path=screenshot)
        assert not errors, errors

        if "tutorials/about_neurodesk/RISE_slideshow.ipynb" in routes:
            target = routes["tutorials/about_neurodesk/RISE_slideshow.ipynb"]
            page.goto(url + "/examples/workflows/RISE_slideshow.html?check=1#test", wait_until="domcontentloaded")
            page.wait_for_url(url + "/" + target + "?check=1#test")
            print("Verified the legacy RISE redirect with its query and fragment")
        browser.close()
        print("Verified launch menu, raw download, page navigation, and Back")
        if widgets:
            print("Verified all five saved NiiVue canvases")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--browser-executable")
    parser.add_argument("--widgets", action="store_true")
    parser.add_argument("--screenshot")
    args = parser.parse_args()
    verify(args.url.rstrip("/"), args.browser_executable, args.widgets, args.screenshot)
