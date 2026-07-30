import discord
from discord import app_commands
from discord.ext import commands

import rewards_db


async def challenge_autocomplete(interaction: discord.Interaction, current: str):
    current = current.lower()
    choices = []
    for c in rewards_db.get_active_challenges():
        if current in c["name"].lower():
            choices.append(app_commands.Choice(name=f"{c['name']} ({c['points']} pts)"[:100], value=str(c["id"])))
    return choices[:25]


async def reward_autocomplete(interaction: discord.Interaction, current: str):
    current = current.lower()
    choices = []
    for r in rewards_db.get_active_rewards():
        if current in r["name"].lower():
            choices.append(app_commands.Choice(name=f"{r['name']} ({r['cost']} pts)"[:100], value=str(r["id"])))
    return choices[:25]


async def _log(guild: discord.Guild, text: str):
    channel_id = rewards_db.get_log_channel_id()
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        try:
            await channel.send(text)
        except Exception as e:
            print(f"Failed to post to rewards log channel: {e}")


class Rewards(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---- points (admin) ----

    @app_commands.command(name="points_give", description="Award points to a creator.")
    @app_commands.describe(member="The creator", amount="Points to award (must be positive)", reason="Why")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def points_give(
        self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1], reason: str
    ):
        rewards_db.add_points(member.id, amount, reason, created_by=interaction.user.id)
        balance = rewards_db.get_balance(member.id)
        await interaction.response.send_message(
            f"✅ Gave {member.display_name} {amount} points for: {reason}. New balance: {balance}.",
            ephemeral=True,
        )
        try:
            await member.send(f"🎉 You earned {amount} points: {reason}. Your balance is now {balance}.")
        except Exception:
            pass
        await _log(interaction.guild, f"➕ {member.mention} awarded {amount} points ({reason}) by {interaction.user.mention}. Balance: {balance}.")

    @app_commands.command(name="points_take", description="Deduct points from a creator.")
    @app_commands.describe(member="The creator", amount="Points to deduct (must be positive)", reason="Why")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def points_take(
        self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1], reason: str
    ):
        rewards_db.add_points(member.id, -amount, reason, created_by=interaction.user.id)
        balance = rewards_db.get_balance(member.id)
        await interaction.response.send_message(
            f"✅ Took {amount} points from {member.display_name} for: {reason}. New balance: {balance}.",
            ephemeral=True,
        )
        try:
            await member.send(f"⚠️ {amount} points were deducted: {reason}. Your balance is now {balance}.")
        except Exception:
            pass
        await _log(interaction.guild, f"➖ {member.mention} lost {amount} points ({reason}) by {interaction.user.mention}. Balance: {balance}.")

    @app_commands.command(name="points_balance", description="Check a points balance (yours, or someone else's).")
    @app_commands.describe(member="Leave blank to check your own balance")
    async def points_balance(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        balance = rewards_db.get_balance(target.id)
        who = "Your" if target == interaction.user else f"{target.display_name}'s"
        await interaction.response.send_message(f"{who} balance: **{balance} points**.", ephemeral=True)

    @app_commands.command(name="points_history", description="See recent points activity (yours, or someone else's).")
    @app_commands.describe(member="Leave blank to check your own history")
    async def points_history(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        history = rewards_db.get_history(target.id, limit=10)
        if not history:
            await interaction.response.send_message("No points activity yet.", ephemeral=True)
            return
        lines = [f"{'+' if h['amount'] >= 0 else ''}{h['amount']} — {h['reason'] or 'no reason given'}" for h in history]
        who = "Your" if target == interaction.user else f"{target.display_name}'s"
        await interaction.response.send_message(
            f"**{who} last {len(history)} transactions:**\n" + "\n".join(lines), ephemeral=True
        )

    @app_commands.command(name="leaderboard", description="See the top point earners.")
    async def leaderboard(self, interaction: discord.Interaction):
        top = rewards_db.get_leaderboard(10)
        if not top:
            await interaction.response.send_message("No points have been awarded yet.", ephemeral=True)
            return
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (user_id, total) in enumerate(top):
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            prefix = medals[i] if i < 3 else f"{i + 1}."
            lines.append(f"{prefix} {name} — {total} points")
        await interaction.response.send_message("**🏆 Leaderboard**\n" + "\n".join(lines))

    @app_commands.command(name="points_log_channel", description="Set the channel where points activity gets logged.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def points_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        rewards_db.set_setting("log_channel_id", str(channel.id))
        await interaction.response.send_message(f"✅ Points activity will log in {channel.mention}.", ephemeral=True)

    # ---- challenges ----

    @app_commands.command(name="challenges", description="See the list of challenges you can complete for points.")
    async def challenges(self, interaction: discord.Interaction):
        active = rewards_db.get_active_challenges()
        if not active:
            await interaction.response.send_message("No challenges are active right now.", ephemeral=True)
            return
        lines = [f"**{c['name']}** — {c['points']} pts\n{c['description'] or ''}".strip() for c in active]
        await interaction.response.send_message("**Available challenges**\n\n" + "\n\n".join(lines), ephemeral=True)

    @app_commands.command(name="challenge_submit", description="Submit a completed challenge for review.")
    @app_commands.describe(challenge="Which challenge", note="Proof or details (e.g. links to your videos)")
    @app_commands.autocomplete(challenge=challenge_autocomplete)
    async def challenge_submit(self, interaction: discord.Interaction, challenge: str, note: str = None):
        challenge_id = int(challenge)
        c = rewards_db.get_challenge(challenge_id)
        if not c or not c["active"]:
            await interaction.response.send_message("⚠️ That challenge isn't available anymore.", ephemeral=True)
            return
        sub_id = rewards_db.submit_challenge(challenge_id, interaction.user.id, note)
        await interaction.response.send_message(
            f"✅ Submitted **{c['name']}** for review (submission #{sub_id}). You'll be notified once it's reviewed.",
            ephemeral=True,
        )
        await _log(
            interaction.guild,
            f"📝 {interaction.user.mention} submitted **{c['name']}** (submission #{sub_id}) for review."
            + (f" Note: {note}" if note else ""),
        )

    @app_commands.command(name="challenge_pending", description="List challenge submissions waiting for review.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def challenge_pending(self, interaction: discord.Interaction):
        pending = rewards_db.get_pending_submissions()
        if not pending:
            await interaction.response.send_message("No pending submissions.", ephemeral=True)
            return
        lines = []
        for s in pending:
            c = rewards_db.get_challenge(s["challenge_id"])
            member = interaction.guild.get_member(s["user_id"])
            name = member.display_name if member else f"User {s['user_id']}"
            line = f"#{s['id']} — {name} — **{c['name'] if c else 'unknown'}** ({c['points'] if c else '?'} pts)"
            if s["note"]:
                line += f"\n  Note: {s['note']}"
            lines.append(line)
        await interaction.response.send_message("**Pending challenge submissions**\n\n" + "\n\n".join(lines), ephemeral=True)

    @app_commands.command(name="challenge_approve", description="Approve a challenge submission and award the points.")
    @app_commands.describe(submission_id="The submission # from /challenge_pending")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def challenge_approve(self, interaction: discord.Interaction, submission_id: int):
        s = rewards_db.get_submission(submission_id)
        if not s or s["status"] != "pending":
            await interaction.response.send_message("⚠️ That submission isn't pending (already reviewed, or doesn't exist).", ephemeral=True)
            return
        c = rewards_db.get_challenge(s["challenge_id"])
        if not c:
            await interaction.response.send_message("⚠️ That challenge no longer exists.", ephemeral=True)
            return

        rewards_db.review_submission(submission_id, "approved", interaction.user.id)
        rewards_db.add_points(s["user_id"], c["points"], f"Challenge: {c['name']}", created_by=interaction.user.id)
        balance = rewards_db.get_balance(s["user_id"])

        member = interaction.guild.get_member(s["user_id"])
        await interaction.response.send_message(
            f"✅ Approved. {(member.display_name if member else s['user_id'])} earned {c['points']} points.",
            ephemeral=True,
        )
        if member:
            try:
                await member.send(f"🎉 Your submission for **{c['name']}** was approved! You earned {c['points']} points. Balance: {balance}.")
            except Exception:
                pass
        await _log(interaction.guild, f"✅ Submission #{submission_id} approved by {interaction.user.mention} — {c['points']} points awarded.")

    @app_commands.command(name="challenge_deny", description="Deny a challenge submission.")
    @app_commands.describe(submission_id="The submission # from /challenge_pending", reason="Optional reason")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def challenge_deny(self, interaction: discord.Interaction, submission_id: int, reason: str = None):
        s = rewards_db.get_submission(submission_id)
        if not s or s["status"] != "pending":
            await interaction.response.send_message("⚠️ That submission isn't pending (already reviewed, or doesn't exist).", ephemeral=True)
            return

        rewards_db.review_submission(submission_id, "denied", interaction.user.id)
        member = interaction.guild.get_member(s["user_id"])
        await interaction.response.send_message("✅ Denied.", ephemeral=True)
        if member:
            try:
                text = "Your challenge submission wasn't approved."
                if reason:
                    text += f" Reason: {reason}"
                await member.send(text)
            except Exception:
                pass
        await _log(interaction.guild, f"❌ Submission #{submission_id} denied by {interaction.user.mention}." + (f" Reason: {reason}" if reason else ""))

    @app_commands.command(name="challenge_add", description="Add a new challenge to the active list.")
    @app_commands.describe(name="Challenge name", points="Points awarded on approval", description="Details for creators")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def challenge_add(self, interaction: discord.Interaction, name: str, points: app_commands.Range[int, 1], description: str = None):
        challenge_id = rewards_db.add_challenge(name, description, points)
        await interaction.response.send_message(f"✅ Added challenge #{challenge_id}: **{name}** ({points} pts).", ephemeral=True)

    @app_commands.command(name="challenge_remove", description="Deactivate a challenge (history is kept).")
    @app_commands.autocomplete(challenge=challenge_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def challenge_remove(self, interaction: discord.Interaction, challenge: str):
        rewards_db.deactivate_challenge(int(challenge))
        await interaction.response.send_message("✅ Deactivated. Past submissions for it are unaffected.", ephemeral=True)

    # ---- rewards catalog + redemption ----

    @app_commands.command(name="rewards", description="See what you can redeem your points for.")
    async def rewards_list(self, interaction: discord.Interaction):
        active = rewards_db.get_active_rewards()
        if not active:
            await interaction.response.send_message("No rewards are available right now.", ephemeral=True)
            return
        lines = [f"**{r['name']}** — {r['cost']} pts\n{r['description'] or ''}".strip() for r in active]
        balance = rewards_db.get_balance(interaction.user.id)
        await interaction.response.send_message(
            f"**Rewards catalog** (your balance: {balance} pts)\n\n" + "\n\n".join(lines), ephemeral=True
        )

    @app_commands.command(name="redeem", description="Spend your points on a reward.")
    @app_commands.describe(reward="What to redeem")
    @app_commands.autocomplete(reward=reward_autocomplete)
    async def redeem(self, interaction: discord.Interaction, reward: str):
        reward_id = int(reward)
        r = rewards_db.get_reward(reward_id)
        if not r or not r["active"]:
            await interaction.response.send_message("⚠️ That reward isn't available anymore.", ephemeral=True)
            return

        balance = rewards_db.get_balance(interaction.user.id)
        if balance < r["cost"]:
            await interaction.response.send_message(
                f"⚠️ You need {r['cost']} points for **{r['name']}** — you have {balance}.", ephemeral=True
            )
            return

        rewards_db.add_points(interaction.user.id, -r["cost"], f"Redeemed: {r['name']}", created_by=interaction.user.id)
        request_id = rewards_db.create_redemption_request(reward_id, interaction.user.id, r["cost"])
        new_balance = rewards_db.get_balance(interaction.user.id)

        await interaction.response.send_message(
            f"✅ Requested **{r['name']}** for {r['cost']} points (request #{request_id}). "
            f"New balance: {new_balance}. A staff member will follow up to fulfill it.",
            ephemeral=True,
        )
        await _log(
            interaction.guild,
            f"🎁 {interaction.user.mention} requested **{r['name']}** ({r['cost']} pts, request #{request_id}). "
            f"Balance now {new_balance}.",
        )

    @app_commands.command(name="redemptions_pending", description="List redemption requests waiting for fulfillment.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def redemptions_pending(self, interaction: discord.Interaction):
        pending = rewards_db.get_pending_redemptions()
        if not pending:
            await interaction.response.send_message("No pending redemptions.", ephemeral=True)
            return
        lines = []
        for req in pending:
            r = rewards_db.get_reward(req["reward_id"])
            member = interaction.guild.get_member(req["user_id"])
            name = member.display_name if member else f"User {req['user_id']}"
            lines.append(f"#{req['id']} — {name} — **{r['name'] if r else 'unknown'}** ({req['cost']} pts)")
        await interaction.response.send_message("**Pending redemptions**\n\n" + "\n".join(lines), ephemeral=True)

    @app_commands.command(name="redemption_fulfill", description="Mark a redemption request as fulfilled.")
    @app_commands.describe(request_id="The request # from /redemptions_pending")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def redemption_fulfill(self, interaction: discord.Interaction, request_id: int):
        req = rewards_db.get_redemption(request_id)
        if not req or req["status"] != "pending":
            await interaction.response.send_message("⚠️ That request isn't pending (already handled, or doesn't exist).", ephemeral=True)
            return

        rewards_db.set_redemption_status(request_id, "fulfilled", interaction.user.id)
        r = rewards_db.get_reward(req["reward_id"])
        member = interaction.guild.get_member(req["user_id"])

        await interaction.response.send_message("✅ Marked fulfilled.", ephemeral=True)
        if member:
            try:
                await member.send(f"🎁 Your redemption for **{r['name'] if r else 'your reward'}** has been fulfilled!")
            except Exception:
                pass
        await _log(interaction.guild, f"✅ Redemption #{request_id} fulfilled by {interaction.user.mention}.")

    @app_commands.command(name="redemption_deny", description="Deny a redemption request and refund the points.")
    @app_commands.describe(request_id="The request # from /redemptions_pending", reason="Optional reason")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def redemption_deny(self, interaction: discord.Interaction, request_id: int, reason: str = None):
        req = rewards_db.get_redemption(request_id)
        if not req or req["status"] != "pending":
            await interaction.response.send_message("⚠️ That request isn't pending (already handled, or doesn't exist).", ephemeral=True)
            return

        rewards_db.add_points(req["user_id"], req["cost"], f"Refund: denied redemption #{request_id}", created_by=interaction.user.id)
        rewards_db.set_redemption_status(request_id, "denied", interaction.user.id)
        r = rewards_db.get_reward(req["reward_id"])
        member = interaction.guild.get_member(req["user_id"])
        new_balance = rewards_db.get_balance(req["user_id"])

        await interaction.response.send_message(f"✅ Denied and refunded {req['cost']} points.", ephemeral=True)
        if member:
            try:
                text = f"Your redemption for **{r['name'] if r else 'that reward'}** was denied and your {req['cost']} points were refunded (balance: {new_balance})."
                if reason:
                    text += f" Reason: {reason}"
                await member.send(text)
            except Exception:
                pass
        await _log(interaction.guild, f"❌ Redemption #{request_id} denied by {interaction.user.mention}, {req['cost']} points refunded.")

    @app_commands.command(name="reward_add", description="Add a new reward to the redemption catalog.")
    @app_commands.describe(name="Reward name", cost="Point cost", description="Details for creators")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reward_add(self, interaction: discord.Interaction, name: str, cost: app_commands.Range[int, 1], description: str = None):
        reward_id = rewards_db.add_reward(name, description, cost)
        await interaction.response.send_message(f"✅ Added reward #{reward_id}: **{name}** ({cost} pts).", ephemeral=True)

    @app_commands.command(name="reward_remove", description="Deactivate a reward (history is kept).")
    @app_commands.autocomplete(reward=reward_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reward_remove(self, interaction: discord.Interaction, reward: str):
        rewards_db.deactivate_reward(int(reward))
        await interaction.response.send_message("✅ Deactivated. Past redemptions of it are unaffected.", ephemeral=True)


async def setup(bot: commands.Bot):
    rewards_db.init_db()
    await bot.add_cog(Rewards(bot))
