#pragma once

#include <string>

#include "../../../logger/logger.hpp"
#include "../../../shell/shell.hpp"

class AbstractFileClient {
  public:
	std::string read(const int& head = 0, const int& tail = 0);

	void write(const std::string& content);

	bool available();

  protected:
	AbstractFileClient(const std::string& path, const std::string& name, const bool& sudo = false, const bool& required = true);

  private:
	std::string path_;
	bool sudo_;
	bool available_;
	Logger logger_;
	Shell& shell = Shell::getInstance();
};
