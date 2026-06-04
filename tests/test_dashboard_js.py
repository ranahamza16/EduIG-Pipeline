"""
Manual Test Steps for Dashboard JavaScript Interactivity

Since setting up headless browsers (Playwright/Selenium) in an automated 
CI environment can be complex or flaky, the frontend JavaScript functionality 
can be verified via the following manual test script:

1. Start the backend:
   $ python run.py --dashboard
   (Or run the Flask app directly: $ python src/dashboard/app.py)

2. Open browser and navigate to http://127.0.0.1:5000/

3. Test Overview Page (index.js):
   - Verify KPI cards populate with numbers.
   - Verify Follower Distribution bar chart renders (charts.js).
   - Verify Source Pie Chart renders (charts.js).
   - Verify "Last synced" timestamp updates in the top right.

4. Test Profiles Page (/profiles):
   - Navigate to Profiles page using the sidebar.
   - Verify table populates with up to 25 profiles.
   - Test Search: Type "a" in the search bar. Wait 300ms. Verify table filters (debounced).
   - Test Sort: Click the sort dropdown (Followers, Posts, etc.), verify table re-renders.
   - Test Sort Order: Click the arrow button next to the sort dropdown, verify order reverses.
   - Test Pagination: Click "Next" button. Verify page 2 loads.

5. Test Profile Detail Page (/profile/<id>):
   - Click "View" on any profile in the table.
   - Verify avatar, bio, and stats load correctly.
   - Verify post grid populates with recent posts and shows hearts/comments icons.

6. Test Compliance Page (/compliance):
   - Navigate to Audit & Compliance.
   - Verify Runs table populates.
   - Verify Security & Audit Events table populates and colored badges match log levels.

7. Test PWA and Connectivity (pwa.js):
   - Open Developer Tools -> Application -> Service Workers.
   - Verify 'sw.js' is registered (Note: requires Task F4 to be fully implemented).
   - Go to Network tab, check "Offline".
   - Verify offline yellow banner appears.
   - Verify sidebar connection indicator turns red and says "Offline (Cached)".
   - Uncheck "Offline", verify banner disappears and indicator turns green.

8. Test Toasts (dashboard.js):
   - Go to Settings page and click "Clear Cache".
   - Verify green toast notification "Cache cleared. Reloading..." appears at the bottom right.
   - Verify page automatically reloads after 1.5 seconds.
"""
