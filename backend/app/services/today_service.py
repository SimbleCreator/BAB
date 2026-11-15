from sqlalchemy.ext.asyncio import AsyncSession

from app.content import motivational_lines
from app.core.timeutil import local_today
from app.engines import activity_engine, checkin_engine
from app.engines.lines_engine import line_of_the_day
from app.models.user import User
from app.repositories import activity_repo, checkin_repo, habit_repo
from app.schemas.today import TodayHabit, TodayNutrition, TodayOut
from app.services import habit_service, milestone_service, nutrition_service, training_service
from app.services.activity_service import to_out
from app.services.common import require_profile


async def get_today(session: AsyncSession, user: User) -> TodayOut:
    profile = await require_profile(session, user)
    await milestone_service.evaluate_and_commit(session, user.id)
    today = local_today(profile.timezone)
    row = await activity_repo.get(session, user.id, today)
    goal_days = await activity_repo.goal_days(session, user.id, profile.daily_step_goal)
    last_checkin = await checkin_repo.latest(session, user.id)
    workout = await training_service.today_brief(session, user, profile, today)
    await session.commit()  # today_brief may have generated this week's plan
    food = await nutrition_service.get_day(session, user, today)
    habits = [
        TodayHabit(id=h.id, type=h.type, availability=st.availability)
        for h in await habit_repo.active(session, user.id)
        for st in [await habit_service.status(session, user, profile, h)]
    ]
    return TodayOut(
        day=today,
        name=profile.name,
        line=line_of_the_day(motivational_lines(), today, user.id),
        step_goal=profile.daily_step_goal,
        current_streak=activity_engine.current_streak(goal_days, today),
        activity=to_out(row, profile) if row else None,
        checkin_due=checkin_engine.checkin_due(last_checkin.day if last_checkin else None, today),
        new_milestones=await milestone_service.unseen(session, user.id),
        workout=workout,
        nutrition=TodayNutrition(
            target_kcal=food.target.calories_kcal,
            eaten_kcal=food.eaten.calories_kcal,
            remaining_kcal=food.remaining_kcal,
            protein_g=food.eaten.protein_g,
            target_protein_g=food.target.protein_g,
        ),
        habits=habits,
    )
