# GitHub cloud APK build

Upload the contents of this folder to the root of a GitHub repository.

1. Open Actions.
2. Select Build Android APK.
3. Click Run workflow.
4. Open the completed run.
5. Under Artifacts, download UG-WiFi-Support-debug-APK.
6. Extract the artifact to get app-debug.apk.

No Gradle wrapper is required: the workflow installs Gradle 8.10 on the GitHub runner.
