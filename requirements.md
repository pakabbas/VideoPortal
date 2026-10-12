# Video Portal — Requirements

## Overview
A video upload and retrieval portal for farm operations. Farmers wear GoPros while working; at the end of the day, managers collect the videos and upload them to the portal. Videos are modified and then made available for download with filtering.

## User Management & Roles
- Admin can create Video Portal users; these users are responsible for creating additional users.
- Besides admin, there are two roles: Manager and Farmer.
- A manager has farmers (employees) under them.

## Upload Flow
- Farmers record video on head-mounted GoPros during farm work.
- Managers collect the GoPro videos and upload them to the portal.
- Every uploaded video must be tagged with the farmer ID (who recorded it) and the uploader ID (who uploaded it), so both are always known.

## Retrieval / Download Flow
- Uploaded videos are modified (processed) before being presented for download.
- Download section includes filters: by date, by time, by manager, and by farmer (farmer filter is an advanced feature).

## Tech Stack
- Backend: Python with Flask
- Frontend: HTML
- Database: MySQL

## Database
- Design the MySQL schema needed for: users (with roles: admin, manager, farmer), the manager–farmer relationship, video uploads (with farmer ID, uploader ID, timestamps), and any fields required to support the date/time/manager/farmer filters.

## Consent & Agreements
1. Consent checkbox on upload: the video upload page has a consent checkbox the manager must check before uploading. It captures a timestamped record that the manager saw and accepted the terms at the moment of upload.
2. Blanket agreement: instead of signing per video, the manager signs one agreement (via DocuSign or Adobe Sign API) that covers all videos he uploads, so signing never blocks an upload. The manager must sign this agreement during sign-up (account creation), before he can upload any videos. The agreement is one-time and covers all future uploads.
