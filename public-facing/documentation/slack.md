# Connect your own Slack workspace

Every Sherlock installation uses the installer's own Slack workspace, authorized connection, and permissions. Downloading the repository does not connect Slack. The person setting it up selects the workspace and decides who can ask Sherlock questions and where it may reply.

## Set up your connection

The current runtime supplies Sherlock's skills, case files, and recall over local MCP. Slack message delivery is supplied by the agent host's separately configured Slack integration. The installer must set up and authorize that connection themselves, even when their host already supports Slack.

1. Choose the Slack workspace for this installation. Confirm that you have the permissions needed to install or authorize the chosen integration; otherwise, have that workspace's administrator complete the installation.
2. Follow your selected host or connector's Slack setup guide. When it requires a Slack app, create and install an app owned by your organization in the workspace you selected. Slack's [app quickstart](https://docs.slack.dev/quickstart/) explains workspace authorization and app installation; it is provider setup guidance, not a Sherlock installer.
3. Review the requested permissions and store that installation's credentials using the host or connector's supported secret-management method. Slack [tokens](https://docs.slack.dev/authentication/tokens/) carry the permissions granted to the installed integration. Do not put their values in the repository, case files, or an agent conversation.
4. Configure the allowed Slack users and channels in the host. Associate their requests with the intended Sherlock organization profile. A channel name alone does not identify the correct workspace or grant access to all cases in a profile.
5. Install the Sherlock MCP service and skills in the same host using the [installation guide](install.md). Check `sherlock_status` to confirm the intended profile before using private case data.

An existing Slack connection is usable only after its owner confirms the workspace, permissions, and profile binding. The local Sherlock service cannot discover or take over a host's Slack credentials automatically.

## Verify your installation

Use a fictional case and a test channel approved by the workspace owner. Ask a permitted user to request that case, check the local recall result, and then verify that the host actually delivered the reply to the intended workspace, channel, and thread. Repeat with a disallowed user/channel and confirm that no private case context is returned.

Record the host version, installation/profile aliases, tested routing, and result without recording tokens or private message contents. Until this test succeeds, describe Slack as configured or awaiting verification, rather than working end to end. The website screenshots are fictional examples.

## Disconnect or change workspaces

Remove the Slack connection from your host and revoke or uninstall it through your own Slack workspace controls when you want to remove provider access. Switching workspaces requires checking the new workspace and profile binding again. Disconnecting Slack does not delete your local Sherlock cases; manage those separately with the [operator commands](operations.md).

## Dedicated Sherlock Slack app

A standalone Slack bot is not included in this preview. The local MCP package supplies no Slack event listener or bot runner; use your agent host's Slack integration and your own authorized workspace connection. See [compatibility.md](compatibility.md) for the exact verified scope.
