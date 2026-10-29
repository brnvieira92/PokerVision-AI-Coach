"""Plano de prática e comparação de janelas temporais, sem usar lucro como habilidade."""
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from pydantic import BaseModel,Field,ConfigDict,model_validator
from .training import Topic,TOPICS,topic_progress


class StudyTask(BaseModel):
    model_config=ConfigDict(frozen=True,extra='forbid')
    topic: Topic
    baseline: int = Field(ge=0)
    goal: int = Field(default=5,ge=1,le=20)


class StudyPlan(BaseModel):
    model_config=ConfigDict(frozen=True,extra='forbid')
    id: str = Field(default_factory=lambda:uuid4().hex)
    created: str = Field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
    tasks: tuple[StudyTask,...] = Field(min_length=1,max_length=8)

    @model_validator(mode='after')
    def unique_topics(self):
        if len({task.topic for task in self.tasks})!=len(self.tasks):
            raise ValueError('O plano não pode repetir um assunto')
        return self


def make_plan(attempts):
    stats=topic_progress(attempts)
    def priority(topic):
        s=stats[topic]
        return (0,s['total']) if s['total']<3 else (1,(s['recent_correct']+1)/(s['recent_total']+2))
    topics=sorted(TOPICS,key=priority)[:3]
    return StudyPlan(tasks=tuple(StudyTask(topic=t,baseline=stats[t]['total']) for t in topics))


def plan_status(plan,attempts):
    stats=topic_progress(attempts)
    return [dict(topic=t.topic,completed=min(t.goal,max(0,stats[t.topic]['total']-t.baseline)),goal=t.goal)
            for t in plan.tasks]


def compare_periods(attempts,days=None,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Informe um instante com fuso horário')
    if days is not None and (type(days) is not int or days<=0):
        raise ValueError('Período inválido')
    current,previous=[],[]
    start=now-timedelta(days=days) if days else None
    before=start-timedelta(days=days) if days else None
    for attempt in attempts:
        instant=datetime.fromisoformat(attempt['created'])
        if instant.tzinfo is None:
            instant=instant.replace(tzinfo=timezone.utc)
        if instant>now:
            continue
        if start is None or instant>=start:
            current.append(attempt)
        elif instant>=before:
            previous.append(attempt)
    a,b=topic_progress(current),topic_progress(previous)
    changes={}
    for key in TOPICS:
        ca,cb=a[key],b[key]
        changes[key]=100*(ca['correct']/ca['total']-cb['correct']/cb['total']) if ca['total'] and cb['total'] else None
    return dict(current=current,previous=previous,stats=a,previous_stats=b,changes=changes)
