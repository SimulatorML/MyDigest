# MyDigest

A news aggregator bot that provides users with personalized, concise daily digests from selected Telegram channels. The service focuses on delivering relevant news content through advanced recommendation systems, offering a minimalistic and ad-free user experience with the option to navigate to the original source.

## Features

- 📰 Aggregate news from multiple Telegram channels
- 🛠️ Create and manage custom digests.
- 📬 Schedule digests to be sent at specific times.
- 🔎 Search news by keywords or categories.
- 📊 Store and analyze user preferences for personalized recommendations.

## Get started

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/SimulatorML/MyDigest
   cd MyDigest
   ```

2. **Setup with Makefile (recommended)**:
   ```bash
   make setup
   source mydigest/bin/activate # On Windows use: mydigest\Scripts\activate
   make run
   ```

3. **Or manual setup with venv**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   pip install -r requirements.txt
   python -m src.bot
   ```

## Development
### Adding a New Feature
1) Create a new branch:
    ```bash
    git checkout -b username/feature-name
    ```
2) Implement your changes in the appropriate module.
3) Puch to origin
    ```bash
    git push origin username/feature-name
    ```
4) Submit a merge request for review.

### Docker run

1) Create an `.env` file with environment variables in the root of the repository using the `.env.sample` template.
2) Create a `dev_scripts/docker_build.sh` file using the `dev_scripts/sample.docker_build.sh` template.
3) Create a `dev_scripts/docker_run.sh` file using the `dev_scripts/sample.docker_run.sh` template.
4. Run the build command
    ```bash
    sh ./dev_scripts/docker_build.sh
    ```
5. Run the docker launch command
    ```bash
    sh ./dev_scripts/docker_run.sh
    ```
6. Use the deployed Bot


## Project structure

1) `data` - данные для работы с ботом
2) `dev_scripts` - скрипты для локальной cборки и запуска сервиса в докер контейнере
3) `notebooks` - jupyter notebooks для экспериментов/тестов/примеров
3) `src` - код проекта
3) `test` - тесты

## The main tools used in the project

![Python](https://img.shields.io/badge/Python_3.12-FFFFFF?style=for-the-badge&logo=python&logoColor=306998&color=000000)
![Aiogram](https://img.shields.io/badge/Aiogram_3.16.0-FFFFFF?style=for-the-badge&logo=Aiogram&logoColor=306998&color=000000)
![Pylint](https://img.shields.io/badge/Pylint_3.3.5-FFFFFF?style=for-the-badge&logo=Pylint&logoColor=306998&color=000000)

![MistralAI](https://img.shields.io/badge/MistralAI_1.5.0-FFFFFF?style=for-the-badge&logo=ai&logoColor=306998&color=000000)
![Supabase](https://img.shields.io/badge/Supabase_2.11.0-FFFFFF?style=for-the-badge&logo=supabase&logoColor=306998&color=000000)

![Pandas](https://img.shields.io/badge/Pandas_2.2.2-FFFFFF?style=for-the-badge&logo=pandas&logoColor=green&color=000000)

