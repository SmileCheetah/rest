export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-orange-50 px-6">
      <section className="max-w-2xl rounded-2xl bg-white p-10 shadow-sm">
        <p className="mb-3 text-sm font-semibold text-orange-600">
          HEAT SAFETY SERVICE
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          폭염 이동 안전 지원 서비스
        </h1>
        <p className="mt-4 leading-7 text-slate-600">
          생활지원사의 방문 일정과 이동 경로를 바탕으로 주변 쉼터와
          쿨링스팟을 안내하는 서비스입니다.
        </p>
        <p className="mt-8 text-sm text-slate-500">
          Frontend 초기 설정이 완료되었습니다.
        </p>
      </section>
    </main>
  );
}
